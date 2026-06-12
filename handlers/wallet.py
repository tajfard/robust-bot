"""Wallet balance, top-up flow."""
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from database.db import get_db
from database.models import User, Transaction, TransactionStatus, PaymentMethod
from services import crypto as crypto_svc
from services import stripe_service
from services.plans import fmt_usd
from utils.helpers import get_user_language
from utils.i18n import t
from config import TRON_WALLET_ADDRESS, ETH_WALLET_ADDRESS, BANK_CARD_NUMBER, BANK_ACCOUNT_NAME, BANK_NAME, ADMIN_IDS

_TOPUP_AMOUNTS = [5, 10, 20, 50]

WAITING_TOPUP_AMOUNT = 10   # kept for bot.py import compatibility
WAITING_TOPUP_RECEIPT = 11


async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message if query else update.message
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        balance = user.wallet_balance if user else 0.0

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_topup_stripe", lang), callback_data="topup_stripe")],
        [InlineKeyboardButton(t("btn_topup_trc20", lang), callback_data="topup_trc20")],
        [InlineKeyboardButton(t("btn_topup_erc20", lang), callback_data="topup_erc20")],
        [InlineKeyboardButton(t("btn_topup_bank", lang), callback_data="topup_bank")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="start")],
    ])
    text = t("wallet_menu", lang, balance=fmt_usd(balance, lang))
    if query:
        await query.answer()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


# ── Crypto top-ups: show address immediately, no amount question ──────────────

async def topup_trc20_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    context.user_data["crypto_pending"] = {
        "mode": "topup",
        "method": "trc20",
        "since_ms": int(time.time() * 1000),
        "cancel_target": "wallet",
    }
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel_crypto")],
    ])
    await query.edit_message_text(
        t("wallet_topup_trc20", lang, address=TRON_WALLET_ADDRESS),
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def topup_erc20_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    context.user_data["crypto_pending"] = {
        "mode": "topup",
        "method": "erc20",
        "since_ts": int(time.time()),
        "cancel_target": "wallet",
    }
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel_crypto")],
    ])
    await query.edit_message_text(
        t("wallet_topup_erc20", lang, address=ETH_WALLET_ADDRESS),
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def topup_check_trc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = get_user_language(update.effective_user.id)
    tg_user = update.effective_user
    since_ms = context.user_data.get("topup_trc20_since_ms", 0)

    # Accept any amount >= 0 (we read actual amount from blockchain)
    result = crypto_svc.check_trc20_payment(since_ms, min_amount_usdt=0)
    if not result:
        await query.answer(t("tx_not_found", lang), show_alert=True)
        return

    tx_hash, actual_amount = result

    if crypto_svc.is_tx_hash_used(tx_hash):
        await query.answer(t("tx_already_used", lang), show_alert=True)
        return

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        user.wallet_balance += actual_amount
        new_balance = user.wallet_balance
        tx = Transaction(
            user_id=user.id,
            amount_usd=actual_amount,
            method=PaymentMethod.USDT_TRC20,
            status=TransactionStatus.CONFIRMED,
            tx_hash=tx_hash,
            confirmed_at=datetime.utcnow(),
        )
        db.add(tx)

    context.user_data.pop("topup_trc20_since_ms", None)
    await query.answer()
    await query.edit_message_text(
        t("wallet_topped_up", lang,
          amount=fmt_usd(actual_amount, lang),
          balance=fmt_usd(new_balance, lang),
          txhash=tx_hash),
        parse_mode="Markdown",
    )


async def topup_check_erc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = get_user_language(update.effective_user.id)
    tg_user = update.effective_user
    since = context.user_data.get("topup_erc20_since", 0)

    result = crypto_svc.check_erc20_payment(since, min_amount_usdt=0)
    if not result:
        await query.answer(t("tx_not_found", lang), show_alert=True)
        return

    tx_hash, actual_amount = result

    if crypto_svc.is_tx_hash_used(tx_hash):
        await query.answer(t("tx_already_used", lang), show_alert=True)
        return

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        user.wallet_balance += actual_amount
        new_balance = user.wallet_balance
        tx = Transaction(
            user_id=user.id,
            amount_usd=actual_amount,
            method=PaymentMethod.USDT_ERC20,
            status=TransactionStatus.CONFIRMED,
            tx_hash=tx_hash,
            confirmed_at=datetime.utcnow(),
        )
        db.add(tx)

    context.user_data.pop("topup_erc20_since", None)
    await query.answer()
    await query.edit_message_text(
        t("wallet_topped_up", lang,
          amount=fmt_usd(actual_amount, lang),
          balance=fmt_usd(new_balance, lang),
          txhash=tx_hash),
        parse_mode="Markdown",
    )


# ── Bank top-up: show bank details → user sends receipt → admin approves ──────

async def topup_bank_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    await query.edit_message_text(
        t("wallet_topup_bank", lang, bank=BANK_NAME, card=BANK_CARD_NUMBER, name=BANK_ACCOUNT_NAME),
        parse_mode="Markdown",
    )
    # Caller (bot.py) sets _topup_conv_active so receipt_router sends the photo here
    return WAITING_TOPUP_RECEIPT


async def topup_bank_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    photo = update.message.photo
    document = update.message.document
    file_id = None
    if photo:
        file_id = photo[-1].file_id
    elif document:
        file_id = document.file_id
    else:
        await update.message.reply_text(t("send_receipt", lang))
        return WAITING_TOPUP_RECEIPT

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        tx = Transaction(
            user_id=user.id,
            amount_usd=0,                    # admin will confirm the actual amount
            method=PaymentMethod.BANK_TRANSFER,
            status=TransactionStatus.PENDING,
            receipt_file_id=file_id,
        )
        db.add(tx)
        db.flush()
        tx_id = tx.id

    for admin_id in ADMIN_IDS:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_topup_{tx_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_topup_{tx_id}"),
        ]])
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=file_id,
            caption=f"💸 *Wallet Top-up Receipt*\n\nUser tg:{tg_user.id}\nTX #{tx_id}",
            reply_markup=kb,
            parse_mode="Markdown",
        )

    await update.message.reply_text(t("wallet_topup_pending", lang))
    return ConversationHandler.END


# ── Stripe wallet top-up ──────────────────────────────────────────────────────

async def topup_stripe_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"${a}", callback_data=f"topup_stripe_amount_{a}")]
         for a in _TOPUP_AMOUNTS] +
        [[InlineKeyboardButton(t("btn_back", lang), callback_data="wallet")]]
    )
    await query.edit_message_text(
        t("topup_stripe_select_amount", lang),
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def topup_stripe_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    tg_user = update.effective_user
    amount = int(query.data.split("_")[-1])

    session_id, url = stripe_service.create_payment_link(
        amount, 0, f"Wallet Top-up ${amount}"
    )
    context.bot_data.setdefault("pending_topup_stripe", {})[tg_user.id] = {
        "session_id": session_id,
        "amount": amount,
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_pay_now", lang), url=url)],
        [InlineKeyboardButton(t("btn_stripe_check", lang), callback_data="check_topup_stripe")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="wallet")],
    ])
    await query.edit_message_text(
        t("topup_stripe_instruction", lang, amount=amount),
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def topup_stripe_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = get_user_language(update.effective_user.id)
    tg_user = update.effective_user

    pending = context.bot_data.get("pending_topup_stripe", {}).get(tg_user.id)
    if not pending:
        await query.answer()
        await query.edit_message_text(t("order_not_found", lang))
        return

    session = stripe_service.retrieve_session(pending["session_id"])
    if session.payment_status != "paid":
        await query.answer(t("stripe_not_paid_yet", lang), show_alert=True)
        return

    await query.answer()
    amount = pending["amount"]

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        user.wallet_balance += amount
        new_balance = user.wallet_balance
        db.add(Transaction(
            user_id=user.id,
            amount_usd=amount,
            method=PaymentMethod.STRIPE,
            status=TransactionStatus.CONFIRMED,
            tx_hash=pending["session_id"],
            confirmed_at=datetime.utcnow(),
        ))

    context.bot_data.get("pending_topup_stripe", {}).pop(tg_user.id, None)
    await query.edit_message_text(
        t("wallet_topped_up", lang,
          amount=fmt_usd(amount, lang),
          balance=fmt_usd(new_balance, lang),
          txhash=pending["session_id"]),
        parse_mode="Markdown",
    )
