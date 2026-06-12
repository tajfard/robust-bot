"""Payment flow handlers for all payment methods."""
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from database.db import get_db
from database.models import Order, OrderStatus, Transaction, TransactionStatus, PaymentMethod, User, Plan
from services import stripe_service, crypto as crypto_svc
from services.plans import fmt_usd
from services.vpn_manager import activate_order
from utils.helpers import get_or_create_user, get_user_language, credentials_keyboard
from utils.i18n import t
from config import (
    TRON_WALLET_ADDRESS, ETH_WALLET_ADDRESS,
    BANK_CARD_NUMBER, BANK_ACCOUNT_NAME, BANK_NAME,
    ADMIN_IDS,
)

WAITING_RECEIPT = 1


def _create_order(
    telegram_id: int,
    plan_id: int,
    method: PaymentMethod,
    renewal_info: dict | None = None,
) -> tuple[int, float, str]:
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        plan = db.get(Plan, plan_id)
        order = Order(
            user_id=user.id,
            plan_id=plan_id,
            status=OrderStatus.PENDING,
            payment_method=method,
            amount_paid=plan.price_usd,
            vpn_username=renewal_info["username"] if renewal_info else None,
            vpn_password=renewal_info["password"] if renewal_info else None,
        )
        db.add(order)
        db.flush()
        return order.id, plan.price_usd, plan.name


def _credit_overpayment(user_id: int, excess: float) -> float:
    """Add excess to the user's wallet and return new balance."""
    with get_db() as db:
        user = db.get(User, user_id)
        user.wallet_balance += excess
        return user.wallet_balance


def _get_user_id_for_order(order_id: int) -> int:
    with get_db() as db:
        order = db.get(Order, order_id)
        return order.user_id


# ── Stripe ────────────────────────────────────────────────────────────────────

async def pay_stripe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = int(query.data.split("_")[2])
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    renewal_info = context.user_data.pop("renewal_info", None)
    order_id, price, plan_name = _create_order(tg_user.id, plan_id, PaymentMethod.STRIPE, renewal_info)
    session_id, url = stripe_service.create_payment_link(price, order_id, f"VPN Plan: {plan_name}")

    # Store session_id so check_stripe can poll Stripe directly
    context.bot_data.setdefault("pending_stripe", {})[order_id] = {
        "session_id": session_id,
        "telegram_id": tg_user.id,
        "amount": price,
    }

    keyboard = [
        [InlineKeyboardButton(t("btn_pay_now", lang), url=url)],
        [InlineKeyboardButton(t("btn_stripe_check", lang), callback_data=f"check_stripe_{order_id}")],
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="plans")],
    ]
    await query.edit_message_text(
        t("stripe_instruction", lang, amount=f"{price:.2f}"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def check_stripe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    order_id = int(query.data.split("_")[2])

    pending = context.bot_data.get("pending_stripe", {}).get(order_id)
    if not pending:
        await query.edit_message_text(t("order_not_found", lang))
        return

    session = stripe_service.retrieve_session(pending["session_id"])
    if session.payment_status != "paid":
        await query.answer(t("stripe_not_paid_yet", lang), show_alert=True)
        return

    # Prevent double-activation
    with get_db() as db:
        order = db.get(Order, order_id)
        if not order or order.status in (OrderStatus.ACTIVE, OrderStatus.EXPIRED):
            await query.edit_message_text(t("order_not_found", lang))
            return
        order.status = OrderStatus.PAID
        tx = Transaction(
            user_id=order.user_id,
            amount_usd=pending["amount"],
            method=PaymentMethod.STRIPE,
            status=TransactionStatus.CONFIRMED,
            tx_hash=pending["session_id"],
            order_id=order_id,
            confirmed_at=datetime.utcnow(),
        )
        db.add(tx)

    context.bot_data.get("pending_stripe", {}).pop(order_id, None)
    activated = activate_order(order_id)

    await query.edit_message_text(
        t("payment_confirmed", lang,
          username=activated.vpn_username,
          password=activated.vpn_password,
          expires=activated.expires_at.strftime("%Y-%m-%d"),
          txhash=pending["session_id"]),
        reply_markup=credentials_keyboard(activated.vpn_username, activated.vpn_password, lang),
        parse_mode="Markdown",
    )


# ── TRC20 ─────────────────────────────────────────────────────────────────────

async def pay_trc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = int(query.data.split("_")[2])
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    renewal_info = context.user_data.pop("renewal_info", None)
    order_id, price, _ = _create_order(tg_user.id, plan_id, PaymentMethod.USDT_TRC20, renewal_info)
    context.bot_data.setdefault("pending_trc20", {})[order_id] = {
        "since_ms": int(time.time() * 1000),
        "amount": price,
        "telegram_id": tg_user.id,
    }

    keyboard = [
        [InlineKeyboardButton(t("btn_sent_check", lang), callback_data=f"check_trc20_{order_id}")],
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="plans")],
    ]
    await query.edit_message_text(
        t("trc20_instruction", lang, amount=f"{price:.2f}", address=TRON_WALLET_ADDRESS),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def check_trc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = get_user_language(update.effective_user.id)
    order_id = int(query.data.split("_")[2])

    pending = context.bot_data.get("pending_trc20", {}).get(order_id)
    if not pending:
        await query.answer()
        await query.edit_message_text(t("order_not_found", lang))
        return

    result = crypto_svc.check_trc20_payment(pending["since_ms"], min_amount_usdt=pending["amount"])
    if not result:
        await query.answer(t("tx_not_found", lang), show_alert=True)
        return

    tx_hash, actual_amount = result

    if crypto_svc.is_tx_hash_used(tx_hash):
        await query.answer(t("tx_already_used", lang), show_alert=True)
        return

    required = pending["amount"]
    excess = round(actual_amount - required, 6)

    with get_db() as db:
        order = db.get(Order, order_id)
        order.status = OrderStatus.PAID
        user_id = order.user_id
        if excess > 0:
            user = db.get(User, user_id)
            user.wallet_balance += excess
            new_balance = user.wallet_balance
        else:
            new_balance = None
        tx = Transaction(
            user_id=user_id,
            amount_usd=actual_amount,
            method=PaymentMethod.USDT_TRC20,
            status=TransactionStatus.CONFIRMED,
            tx_hash=tx_hash,
            order_id=order_id,
            confirmed_at=datetime.utcnow(),
        )
        db.add(tx)

    activated = activate_order(order_id)
    await query.answer()

    msg = t("payment_confirmed", lang,
            username=activated.vpn_username,
            password=activated.vpn_password,
            expires=activated.expires_at.strftime("%Y-%m-%d"),
            txhash=tx_hash)
    if excess > 0:
        msg += "\n\n" + t("overpayment_credited", lang,
                           excess=fmt_usd(excess, lang), balance=fmt_usd(new_balance, lang))
    await query.edit_message_text(
        msg,
        reply_markup=credentials_keyboard(activated.vpn_username, activated.vpn_password, lang),
        parse_mode="Markdown",
    )


# ── ERC20 ─────────────────────────────────────────────────────────────────────

async def pay_erc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = int(query.data.split("_")[2])
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    renewal_info = context.user_data.pop("renewal_info", None)
    order_id, price, _ = _create_order(tg_user.id, plan_id, PaymentMethod.USDT_ERC20, renewal_info)
    context.bot_data.setdefault("pending_erc20", {})[order_id] = {
        "since": int(time.time()),
        "amount": price,
        "telegram_id": tg_user.id,
    }

    keyboard = [
        [InlineKeyboardButton(t("btn_sent_check", lang), callback_data=f"check_erc20_{order_id}")],
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="plans")],
    ]
    await query.edit_message_text(
        t("erc20_instruction", lang, amount=f"{price:.2f}", address=ETH_WALLET_ADDRESS),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def check_erc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = get_user_language(update.effective_user.id)
    order_id = int(query.data.split("_")[2])

    pending = context.bot_data.get("pending_erc20", {}).get(order_id)
    if not pending:
        await query.answer()
        await query.edit_message_text(t("order_not_found", lang))
        return

    result = crypto_svc.check_erc20_payment(pending["since"], min_amount_usdt=pending["amount"])
    if not result:
        await query.answer(t("tx_not_found", lang), show_alert=True)
        return

    tx_hash, actual_amount = result

    if crypto_svc.is_tx_hash_used(tx_hash):
        await query.answer(t("tx_already_used", lang), show_alert=True)
        return

    required = pending["amount"]
    excess = round(actual_amount - required, 6)

    with get_db() as db:
        order = db.get(Order, order_id)
        order.status = OrderStatus.PAID
        user_id = order.user_id
        if excess > 0:
            user = db.get(User, user_id)
            user.wallet_balance += excess
            new_balance = user.wallet_balance
        else:
            new_balance = None
        tx = Transaction(
            user_id=user_id,
            amount_usd=actual_amount,
            method=PaymentMethod.USDT_ERC20,
            status=TransactionStatus.CONFIRMED,
            tx_hash=tx_hash,
            order_id=order_id,
            confirmed_at=datetime.utcnow(),
        )
        db.add(tx)

    activated = activate_order(order_id)
    await query.answer()

    msg = t("payment_confirmed", lang,
            username=activated.vpn_username,
            password=activated.vpn_password,
            expires=activated.expires_at.strftime("%Y-%m-%d"),
            txhash=tx_hash)
    if excess > 0:
        msg += "\n\n" + t("overpayment_credited", lang,
                           excess=fmt_usd(excess, lang), balance=fmt_usd(new_balance, lang))
    await query.edit_message_text(
        msg,
        reply_markup=credentials_keyboard(activated.vpn_username, activated.vpn_password, lang),
        parse_mode="Markdown",
    )


# ── Wallet ────────────────────────────────────────────────────────────────────

async def pay_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = int(query.data.split("_")[2])
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    renewal_info = context.user_data.pop("renewal_info", None)

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        plan = db.get(Plan, plan_id)

        if user.wallet_balance < plan.price_usd:
            await query.edit_message_text(
                t("wallet_insufficient", lang,
                  required=fmt_usd(plan.price_usd, lang),
                  balance=fmt_usd(user.wallet_balance, lang)),
                parse_mode="Markdown",
            )
            return

        user.wallet_balance -= plan.price_usd
        order = Order(
            user_id=user.id,
            plan_id=plan_id,
            status=OrderStatus.PAID,
            payment_method=PaymentMethod.WALLET,
            amount_paid=plan.price_usd,
            vpn_username=renewal_info["username"] if renewal_info else None,
            vpn_password=renewal_info["password"] if renewal_info else None,
        )
        db.add(order)
        db.flush()
        order_id = order.id

    activated = activate_order(order_id)
    await query.edit_message_text(
        t("wallet_activated", lang,
          username=activated.vpn_username,
          password=activated.vpn_password,
          expires=activated.expires_at.strftime("%Y-%m-%d")),
        reply_markup=credentials_keyboard(activated.vpn_username, activated.vpn_password, lang),
        parse_mode="Markdown",
    )


# ── Bank Transfer ─────────────────────────────────────────────────────────────

async def pay_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = int(query.data.split("_")[2])
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    renewal_info = context.user_data.pop("renewal_info", None)
    order_id, price, _ = _create_order(tg_user.id, plan_id, PaymentMethod.BANK_TRANSFER, renewal_info)
    context.user_data["bank_order_id"] = order_id

    await query.edit_message_text(
        t("bank_instruction", lang,
          amount=f"{price:.2f}",
          bank=BANK_NAME, card=BANK_CARD_NUMBER, name=BANK_ACCOUNT_NAME),
        parse_mode="Markdown",
    )
    return WAITING_RECEIPT


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("bank_order_id")
    lang = get_user_language(update.effective_user.id)

    if not order_id:
        await update.message.reply_text(t("order_not_found", lang))
        return ConversationHandler.END

    photo = update.message.photo
    document = update.message.document
    file_id = None
    if photo:
        file_id = photo[-1].file_id
    elif document:
        file_id = document.file_id
    else:
        await update.message.reply_text(t("send_receipt", lang))
        return WAITING_RECEIPT

    with get_db() as db:
        order = db.get(Order, order_id)
        tx = Transaction(
            user_id=order.user_id,
            amount_usd=0,                    # admin confirms actual amount
            method=PaymentMethod.BANK_TRANSFER,
            status=TransactionStatus.PENDING,
            order_id=order_id,
            receipt_file_id=file_id,
        )
        db.add(tx)
        db.flush()
        tx_id = tx.id
        tg_id = order.user.telegram_id
        plan_name = order.plan.name
        plan_price = order.plan.price_usd

    for admin_id in ADMIN_IDS:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_bank_{tx_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_bank_{tx_id}"),
        ]])
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=file_id,
            caption=(
                f"💸 *Bank Transfer Receipt*\n\n"
                f"Order #{order_id} | tg:{tg_id}\n"
                f"Plan: {plan_name} (${plan_price:.2f})\n"
                f"TX #{tx_id} — enter amount + receipt number to approve"
            ),
            reply_markup=kb,
            parse_mode="Markdown",
        )

    await update.message.reply_text(t("receipt_received", lang))
    context.user_data.pop("bank_order_id", None)
    return ConversationHandler.END
