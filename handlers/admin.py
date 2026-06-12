"""Admin panel — approve/reject payments, manage plans, stats."""
from datetime import datetime
from sqlalchemy import func
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from database.db import get_db
from database.models import (
    Transaction, TransactionStatus, Order, OrderStatus,
    User, Plan, PaymentMethod,
)
from services.vpn_manager import activate_order
from services.plans import fmt_usd
from utils.helpers import get_user_language, credentials_keyboard
from utils.i18n import t
from config import ADMIN_IDS

(
    ADD_PLAN_NAME, ADD_PLAN_PRICE, ADD_PLAN_DAYS,
    ADD_PLAN_BANDWIDTH, ADD_PLAN_CONNECTIONS, ADD_PLAN_DESC,
) = range(20, 26)

# Admin approval conversation states
APPROVE_WAITING_AMOUNT = 40
APPROVE_WAITING_RECEIPT = 41

# Per-admin pending approval context: {admin_tg_id: {"tx_id": int, "type": "order"|"topup"}}
_pending_approvals: dict[int, dict] = {}


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


def require_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            lang = get_user_language(update.effective_user.id)
            msg = update.message or update.callback_query.message
            await msg.reply_text(t("admin_only", lang))
            return
        return await func(update, context)
    return wrapper


@require_admin
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")],
        [InlineKeyboardButton("💸 پرداخت‌های در انتظار", callback_data="admin_pending")],
    ]
    msg = update.message or update.callback_query.message
    await msg.reply_text("🛠 *پنل ادمین*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def notify_admins_purchase(bot, activated, method: str):
    """Send a new-purchase notification to all admins."""
    text = (
        f"🛒 *خرید جدید*\n\n"
        f"👤 کاربر: `{activated.telegram_id}`\n"
        f"📦 پلن: {activated.plan_name}\n"
        f"💳 روش پرداخت: {method}\n"
        f"💰 مبلغ: ${activated.amount_paid:.2f}\n"
        f"🔐 نام کاربری: `{activated.vpn_username}`\n"
        f"📅 انقضا: {activated.expires_at.strftime('%Y-%m-%d')}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="Markdown")
        except Exception:
            pass


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    paid_statuses = [OrderStatus.ACTIVE, OrderStatus.EXPIRED]

    with get_db() as db:
        total_users    = db.query(User).count()
        new_today      = db.query(User).filter(User.created_at >= today).count()

        successful_q = (
            db.query(Order)
            .join(Order.plan)
            .filter(Order.status.in_(paid_statuses), Plan.is_test == False)
        )
        total_successful  = successful_q.count()
        today_successful  = successful_q.filter(Order.activated_at >= today).count()
        active_now        = db.query(Order).filter(Order.status == OrderStatus.ACTIVE).count()
        test_used         = (
            db.query(Order)
            .join(Order.plan)
            .filter(Order.status.in_(paid_statuses), Plan.is_test == True)
            .count()
        )

        revenue_total = successful_q.with_entities(
            func.sum(Order.amount_paid)
        ).scalar() or 0.0
        revenue_today = (
            db.query(func.sum(Order.amount_paid))
            .join(Order.plan)
            .filter(
                Order.status.in_(paid_statuses),
                Plan.is_test == False,
                Order.activated_at >= today,
            )
            .scalar() or 0.0
        )

    text = (
        f"📊 *آمار ربات*\n\n"
        f"👥 *کاربران*\n"
        f"  کل: {total_users}\n"
        f"  امروز: +{new_today}\n\n"
        f"📦 *سفارشات موفق*\n"
        f"  کل: {total_successful}\n"
        f"  امروز: +{today_successful}\n"
        f"  فعال الان: {active_now}\n"
        f"  اکانت تست: {test_used}\n\n"
        f"💰 *درآمد*\n"
        f"  کل: ${revenue_total:.2f}\n"
        f"  امروز: ${revenue_today:.2f}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_stats")],
        [InlineKeyboardButton("💸 پرداخت‌های در انتظار", callback_data="admin_pending")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def admin_pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    with get_db() as db:
        pending = db.query(Transaction).filter(Transaction.status == TransactionStatus.PENDING).all()

    if not pending:
        await query.edit_message_text(t("no_pending", "en"))
        return

    for tx in pending:
        kind = "Order" if tx.order_id else "Wallet top-up"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_bank_{tx.id}" if tx.order_id else f"approve_topup_{tx.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_bank_{tx.id}" if tx.order_id else f"reject_topup_{tx.id}"),
        ]])
        text = f"TX #{tx.id} | {kind}\nStatus: pending"
        if tx.receipt_file_id:
            await query.message.reply_photo(photo=tx.receipt_file_id, caption=text, reply_markup=kb)
        else:
            await query.message.reply_text(text, reply_markup=kb)


# ── Approval conversation: amount → receipt number → process ─────────────────

async def start_approve_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry: admin taps Approve on an order bank transfer."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    tx_id = int(query.data.split("_")[2])
    admin_id = query.from_user.id

    with get_db() as db:
        tx = db.get(Transaction, tx_id)
        if not tx or tx.status != TransactionStatus.PENDING:
            await query.message.reply_text(t("already_processed", "en"))
            return

    _pending_approvals[admin_id] = {"tx_id": tx_id, "type": "order", "state": "amount"}
    await query.message.reply_text(t("admin_ask_amount", "en"))
    return APPROVE_WAITING_AMOUNT


async def start_approve_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry: admin taps Approve on a wallet top-up."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    tx_id = int(query.data.split("_")[2])
    admin_id = query.from_user.id

    with get_db() as db:
        tx = db.get(Transaction, tx_id)
        if not tx or tx.status != TransactionStatus.PENDING:
            await query.message.reply_text(t("already_processed", "en"))
            return

    _pending_approvals[admin_id] = {"tx_id": tx_id, "type": "topup", "state": "amount"}
    await query.message.reply_text(t("admin_ask_amount", "en"))
    return APPROVE_WAITING_AMOUNT


async def approve_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in _pending_approvals:
        return

    try:
        amount = float(update.message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(t("admin_invalid_amount", "en"))
        return APPROVE_WAITING_AMOUNT

    _pending_approvals[admin_id]["amount"] = amount
    await update.message.reply_text(t("admin_ask_receipt_number", "en"))
    return APPROVE_WAITING_RECEIPT


async def approve_receipt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in _pending_approvals:
        return

    receipt_number = update.message.text.strip()

    # Check receipt number uniqueness
    with get_db() as db:
        duplicate = db.query(Transaction).filter(
            Transaction.receipt_number == receipt_number
        ).first()
    if duplicate:
        await update.message.reply_text(t("admin_receipt_already_used", "en"))
        return APPROVE_WAITING_RECEIPT

    pending = _pending_approvals.pop(admin_id)
    tx_id = pending["tx_id"]
    amount = pending["amount"]
    kind = pending["type"]

    if kind == "order":
        await _finalize_order_approval(update, context, tx_id, amount, receipt_number)
    else:
        await _finalize_topup_approval(update, context, tx_id, amount, receipt_number)

    return ConversationHandler.END


async def _finalize_order_approval(update, context, tx_id: int, amount: float, receipt_number: str):
    with get_db() as db:
        tx = db.get(Transaction, tx_id)
        if not tx:
            await update.message.reply_text("TX not found.")
            return
        tx.status = TransactionStatus.CONFIRMED
        tx.amount_usd = amount
        tx.receipt_number = receipt_number
        tx.confirmed_at = datetime.utcnow()
        order = db.get(Order, tx.order_id)
        order.amount_paid = amount
        order_id = tx.order_id
        user_tg_id = tx.user.telegram_id
        user_lang = tx.user.language or "fa"

    activated = activate_order(order_id)
    await notify_admins_purchase(context.bot, activated, "Bank Transfer")
    await update.message.reply_text(
        f"✅ Order #{order_id} approved.\nAmount: ${amount:.2f} | Receipt: {receipt_number}"
    )
    await context.bot.send_message(
        chat_id=user_tg_id,
        text=t("bank_approved", user_lang,
               username=activated.vpn_username,
               password=activated.vpn_password,
               expires=activated.expires_at.strftime("%Y-%m-%d")),
        reply_markup=credentials_keyboard(activated.vpn_username, activated.vpn_password, user_lang),
        parse_mode="Markdown",
    )


async def _finalize_topup_approval(update, context, tx_id: int, amount: float, receipt_number: str):
    with get_db() as db:
        tx = db.get(Transaction, tx_id)
        if not tx:
            await update.message.reply_text("TX not found.")
            return
        tx.status = TransactionStatus.CONFIRMED
        tx.amount_usd = amount
        tx.receipt_number = receipt_number
        tx.confirmed_at = datetime.utcnow()
        user = db.get(User, tx.user_id)
        user.wallet_balance += amount
        new_balance = user.wallet_balance
        user_tg_id = user.telegram_id
        user_lang = user.language or "fa"

    await update.message.reply_text(
        f"✅ Wallet top-up approved.\nAmount: ${amount:.2f} | Receipt: {receipt_number}"
    )
    await context.bot.send_message(
        chat_id=user_tg_id,
        text=t("topup_approved", user_lang,
               amount=fmt_usd(amount, user_lang),
               balance=fmt_usd(new_balance, user_lang)),
        parse_mode="Markdown",
    )


# ── Reject handlers ───────────────────────────────────────────────────────────

async def reject_bank_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    tx_id = int(query.data.split("_")[2])

    with get_db() as db:
        tx = db.get(Transaction, tx_id)
        if not tx:
            return
        tx.status = TransactionStatus.REJECTED
        if tx.order_id:
            order = db.get(Order, tx.order_id)
            if order:
                order.status = OrderStatus.CANCELLED
        user_tg_id = tx.user.telegram_id
        user_lang = tx.user.language or "fa"

    await query.edit_message_caption(f"❌ Rejected TX #{tx_id}")
    await context.bot.send_message(chat_id=user_tg_id, text=t("bank_rejected", user_lang))


async def reject_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    tx_id = int(query.data.split("_")[2])

    with get_db() as db:
        tx = db.get(Transaction, tx_id)
        if not tx:
            return
        tx.status = TransactionStatus.REJECTED
        user_tg_id = tx.user.telegram_id
        user_lang = tx.user.language or "fa"

    await query.edit_message_caption(f"❌ Top-up rejected TX #{tx_id}")
    await context.bot.send_message(chat_id=user_tg_id, text=t("topup_rejected", user_lang))


# ── Approval ConversationHandler ──────────────────────────────────────────────

approve_conv = ConversationHandler(
    entry_points=[],   # started programmatically from start_approve_bank / start_approve_topup
    states={
        APPROVE_WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, approve_amount_received)],
        APPROVE_WAITING_RECEIPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, approve_receipt_received)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: (
        _pending_approvals.pop(u.effective_user.id, None),
        ConversationHandler.END
    )[-1])],
    per_user=True,
    per_chat=True,
)


# ── Add plan conversation ─────────────────────────────────────────────────────

@require_admin
async def add_plan_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 *New Plan*\n\nEnter the plan name:", parse_mode="Markdown")
    return ADD_PLAN_NAME


async def add_plan_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_plan"] = {"name": update.message.text.strip()}
    await update.message.reply_text("Enter price in USD (e.g. `9.99`):", parse_mode="Markdown")
    return ADD_PLAN_PRICE


async def add_plan_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_plan"]["price_usd"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid price. Enter a number like `9.99`:")
        return ADD_PLAN_PRICE
    await update.message.reply_text("Enter duration in days (e.g. `30`):")
    return ADD_PLAN_DAYS


async def add_plan_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_plan"]["duration_days"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid. Enter a whole number like `30`:")
        return ADD_PLAN_DAYS
    await update.message.reply_text("Enter bandwidth in GB (enter `0` for unlimited):")
    return ADD_PLAN_BANDWIDTH


async def add_plan_bandwidth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_plan"]["bandwidth_gb"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid. Enter a whole number:")
        return ADD_PLAN_BANDWIDTH
    await update.message.reply_text("Simultaneous connections (e.g. `1`):")
    return ADD_PLAN_CONNECTIONS


async def add_plan_connections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_plan"]["simultaneous_connections"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid. Enter a whole number:")
        return ADD_PLAN_CONNECTIONS
    await update.message.reply_text("Short description (or `-` to skip):")
    return ADD_PLAN_DESC


async def add_plan_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    plan_data = context.user_data.pop("new_plan")
    plan_data["description"] = None if desc == "-" else desc

    with get_db() as db:
        plan = Plan(**plan_data)
        db.add(plan)
        db.flush()
        plan_id = plan.id

    await update.message.reply_text(
        f"✅ Plan *{plan_data['name']}* created (ID #{plan_id}).",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


add_plan_conv = ConversationHandler(
    entry_points=[CommandHandler("addplan", add_plan_start)],
    states={
        ADD_PLAN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_plan_name)],
        ADD_PLAN_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_plan_price)],
        ADD_PLAN_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_plan_days)],
        ADD_PLAN_BANDWIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_plan_bandwidth)],
        ADD_PLAN_CONNECTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_plan_connections)],
        ADD_PLAN_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_plan_desc)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
