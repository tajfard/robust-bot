"""Payment flow handlers for all payment methods."""
import re
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
from handlers.admin import notify_admins_purchase

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
    lang = get_user_language(update.effective_user.id)
    order_id = int(query.data.split("_")[2])

    pending = context.bot_data.get("pending_stripe", {}).get(order_id)
    if not pending:
        await query.answer()
        await query.edit_message_text(t("order_not_found", lang))
        return

    session = stripe_service.retrieve_session(pending["session_id"])
    if session.payment_status != "paid":
        await query.answer(t("stripe_not_paid_yet", lang), show_alert=True)
        return

    await query.answer()

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
    await notify_admins_purchase(context.bot, activated, "Stripe")

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
    since_ms = int(time.time() * 1000)
    context.user_data["crypto_pending"] = {
        "mode": "purchase",
        "method": "trc20",
        "order_id": order_id,
        "amount": price,
        "since_ms": since_ms,
        "cancel_target": "plans",
    }

    keyboard = [
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
    since_ts = int(time.time())
    context.user_data["crypto_pending"] = {
        "mode": "purchase",
        "method": "erc20",
        "order_id": order_id,
        "amount": price,
        "since_ts": since_ts,
        "cancel_target": "plans",
    }

    keyboard = [
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
            back_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(t("btn_pay_stripe", lang), callback_data=f"pay_stripe_{plan_id}")],
                [InlineKeyboardButton(t("btn_pay_trc20", lang),  callback_data=f"pay_trc20_{plan_id}")],
                [InlineKeyboardButton(t("btn_pay_erc20", lang),  callback_data=f"pay_erc20_{plan_id}")],
                [InlineKeyboardButton(t("btn_pay_bank", lang),   callback_data=f"pay_bank_{plan_id}")],
                [InlineKeyboardButton(t("btn_back_to_plans", lang), callback_data="plans")],
            ])
            await query.edit_message_text(
                t("wallet_insufficient", lang,
                  required=fmt_usd(plan.price_usd, lang),
                  balance=fmt_usd(user.wallet_balance, lang)),
                reply_markup=back_kb,
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
    await notify_admins_purchase(context.bot, activated, "Wallet")
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


# ── Crypto hash submission ────────────────────────────────────────────────────

def _extract_tx_hash(text: str, method: str) -> str | None:
    text = text.strip()
    if method == "trc20":
        m = re.search(r'([0-9a-fA-F]{64})', text)
        return m.group(1) if m else None
    elif method == "erc20":
        m = re.search(r'(0x[0-9a-fA-F]{64})', text, re.IGNORECASE)
        return m.group(1).lower() if m else None
    return None


def _crypto_retry_keyboard(lang: str, has_last_hash: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if has_last_hash:
        rows.append([InlineKeyboardButton(t("btn_check_again", lang), callback_data="check_hash_again")])
    rows.append([InlineKeyboardButton(t("btn_enter_new_hash", lang), callback_data="retry_crypto")])
    rows.append([InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel_crypto")])
    return InlineKeyboardMarkup(rows)


async def receive_crypto_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle TX hash submitted as a text message during a crypto payment or top-up flow."""
    lang = get_user_language(update.effective_user.id)
    pending = context.user_data.get("crypto_pending")
    if not pending:
        return

    mode = pending.get("mode", "purchase")
    method = pending["method"]
    pm = PaymentMethod.USDT_TRC20 if method == "trc20" else PaymentMethod.USDT_ERC20

    last_hash = context.user_data.get("crypto_last_hash")

    tx_hash = _extract_tx_hash(update.message.text or "", method)
    if not tx_hash:
        await update.message.reply_text(
            t("invalid_tx_hash", lang),
            reply_markup=_crypto_retry_keyboard(lang, has_last_hash=bool(last_hash)),
        )
        return

    context.user_data["crypto_last_hash"] = tx_hash

    if crypto_svc.is_tx_hash_used(tx_hash):
        await update.message.reply_text(
            t("tx_already_used", lang),
            reply_markup=_crypto_retry_keyboard(lang, has_last_hash=True),
        )
        return

    min_amount = pending.get("amount", 0) if mode == "purchase" else 0
    if method == "trc20":
        result = crypto_svc.verify_trc20_tx(tx_hash, min_amount, pending.get("since_ms", 0))
    else:
        result = crypto_svc.verify_erc20_tx(tx_hash, min_amount, pending.get("since_ts", 0))

    if not result:
        await update.message.reply_text(
            t("tx_not_found", lang),
            reply_markup=_crypto_retry_keyboard(lang, has_last_hash=True),
        )
        return

    tx_hash, actual_amount = result
    context.user_data.pop("crypto_pending", None)
    context.user_data.pop("crypto_last_hash", None)

    if mode == "topup":
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
            user.wallet_balance += actual_amount
            new_balance = user.wallet_balance
            db.add(Transaction(
                user_id=user.id,
                amount_usd=actual_amount,
                method=pm,
                status=TransactionStatus.CONFIRMED,
                tx_hash=tx_hash,
                confirmed_at=datetime.utcnow(),
            ))
        await update.message.reply_text(
            t("wallet_topped_up", lang,
              amount=fmt_usd(actual_amount, lang),
              balance=fmt_usd(new_balance, lang),
              txhash=tx_hash),
            parse_mode="Markdown",
        )
        return

    # mode == "purchase"
    order_id = pending["order_id"]
    amount = pending["amount"]
    excess = round(actual_amount - amount, 6)

    with get_db() as db:
        order = db.get(Order, order_id)
        if not order or order.status in (OrderStatus.ACTIVE, OrderStatus.EXPIRED):
            await update.message.reply_text(t("order_not_found", lang))
            return
        order.status = OrderStatus.PAID
        user_id = order.user_id
        if excess > 0:
            user = db.get(User, user_id)
            user.wallet_balance += excess
            new_balance = user.wallet_balance
        else:
            new_balance = None
        db.add(Transaction(
            user_id=user_id,
            amount_usd=actual_amount,
            method=pm,
            status=TransactionStatus.CONFIRMED,
            tx_hash=tx_hash,
            order_id=order_id,
            confirmed_at=datetime.utcnow(),
        ))

    activated = activate_order(order_id)
    method_label = "USDT TRC20" if method == "trc20" else "USDT ERC20"
    await notify_admins_purchase(context.bot, activated, method_label)
    msg = t("payment_confirmed", lang,
            username=activated.vpn_username,
            password=activated.vpn_password,
            expires=activated.expires_at.strftime("%Y-%m-%d"),
            txhash=tx_hash)
    if excess > 0:
        msg += "\n\n" + t("overpayment_credited", lang,
                           excess=fmt_usd(excess, lang), balance=fmt_usd(new_balance, lang))
    await update.message.reply_text(
        msg,
        reply_markup=credentials_keyboard(activated.vpn_username, activated.vpn_password, lang),
        parse_mode="Markdown",
    )


async def check_hash_again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Re-verify the last submitted TX hash."""
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    pending = context.user_data.get("crypto_pending")
    last_hash = context.user_data.get("crypto_last_hash")

    if not pending or not last_hash:
        await query.edit_message_text(
            t("retry_hash_prompt", lang),
            reply_markup=_crypto_retry_keyboard(lang, has_last_hash=False),
        )
        return

    mode = pending.get("mode", "purchase")
    method = pending["method"]
    min_amount = pending.get("amount", 0) if mode == "purchase" else 0

    if method == "trc20":
        result = crypto_svc.verify_trc20_tx(last_hash, min_amount, pending.get("since_ms", 0))
    else:
        result = crypto_svc.verify_erc20_tx(last_hash, min_amount, pending.get("since_ts", 0))

    if not result:
        await query.edit_message_text(
            t("tx_not_found", lang),
            reply_markup=_crypto_retry_keyboard(lang, has_last_hash=True),
        )
        return

    await query.answer()
    _, actual_amount = result
    pm = PaymentMethod.USDT_TRC20 if method == "trc20" else PaymentMethod.USDT_ERC20
    context.user_data.pop("crypto_pending", None)
    context.user_data.pop("crypto_last_hash", None)

    if mode == "topup":
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
            user.wallet_balance += actual_amount
            new_balance = user.wallet_balance
            db.add(Transaction(
                user_id=user.id,
                amount_usd=actual_amount,
                method=pm,
                status=TransactionStatus.CONFIRMED,
                tx_hash=last_hash,
                confirmed_at=datetime.utcnow(),
            ))
        await query.edit_message_text(
            t("wallet_topped_up", lang,
              amount=fmt_usd(actual_amount, lang),
              balance=fmt_usd(new_balance, lang),
              txhash=last_hash),
            parse_mode="Markdown",
        )
        return

    order_id = pending["order_id"]
    amount = pending["amount"]
    excess = round(actual_amount - amount, 6)
    with get_db() as db:
        order = db.get(Order, order_id)
        if not order or order.status in (OrderStatus.ACTIVE, OrderStatus.EXPIRED):
            await query.edit_message_text(t("order_not_found", lang))
            return
        order.status = OrderStatus.PAID
        user_id = order.user_id
        if excess > 0:
            user = db.get(User, user_id)
            user.wallet_balance += excess
            new_balance = user.wallet_balance
        else:
            new_balance = None
        db.add(Transaction(
            user_id=user_id,
            amount_usd=actual_amount,
            method=pm,
            status=TransactionStatus.CONFIRMED,
            tx_hash=last_hash,
            order_id=order_id,
            confirmed_at=datetime.utcnow(),
        ))
    activated = activate_order(order_id)
    method_label = "USDT TRC20" if method == "trc20" else "USDT ERC20"
    await notify_admins_purchase(context.bot, activated, method_label)
    msg = t("payment_confirmed", lang,
            username=activated.vpn_username,
            password=activated.vpn_password,
            expires=activated.expires_at.strftime("%Y-%m-%d"),
            txhash=last_hash)
    if excess > 0:
        msg += "\n\n" + t("overpayment_credited", lang,
                           excess=fmt_usd(excess, lang), balance=fmt_usd(new_balance, lang))
    await query.edit_message_text(
        msg,
        reply_markup=credentials_keyboard(activated.vpn_username, activated.vpn_password, lang),
        parse_mode="Markdown",
    )


async def retry_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt the user to paste a new TX hash."""
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    pending = context.user_data.get("crypto_pending")
    if not pending:
        await query.edit_message_text(t("order_not_found", lang))
        return
    await query.edit_message_text(t("retry_hash_prompt", lang))


async def cancel_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending crypto payment/top-up and return to the appropriate menu."""
    query = update.callback_query
    await query.answer()
    pending = context.user_data.pop("crypto_pending", None)
    context.user_data.pop("crypto_last_hash", None)
    cancel_target = (pending or {}).get("cancel_target", "plans")
    if cancel_target == "wallet":
        from handlers.wallet import wallet_menu
        await wallet_menu(update, context)
    else:
        from handlers.plans import show_plans
        await show_plans(update, context)
