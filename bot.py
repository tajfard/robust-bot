import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)

from config import BOT_TOKEN
from database.db import init_db, engine
from handlers.start import start, help_command, choose_language_callback, set_language_callback, show_reviews
from handlers.plans import show_plans, plan_detail, my_orders, order_detail, activate_test_plan
from handlers.renewal import show_renewal_accounts, renewal_account_selected, renewal_plan_selected
from handlers.usage import show_usage_accounts, show_account_usage
from handlers.payment import (
    pay_stripe, check_stripe,
    pay_trc20, check_trc20,
    pay_erc20, check_erc20,
    pay_wallet, pay_bank, receive_receipt,
)
from handlers.wallet import (
    wallet_menu,
    topup_trc20_start, topup_erc20_start, topup_bank_start,
    topup_check_trc20, topup_check_erc20, topup_bank_receipt,
    WAITING_TOPUP_RECEIPT,
)
from handlers.admin import (
    admin_menu, admin_stats, admin_pending_payments,
    start_approve_bank, start_approve_topup,
    reject_bank_payment, reject_topup,
    approve_amount_received, approve_receipt_received,
    _pending_approvals,
    APPROVE_WAITING_AMOUNT, APPROVE_WAITING_RECEIPT,
)
from services.plans import seed_plans
from services.vpn_manager import check_and_expire_orders

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _run_migrations():
    from sqlalchemy import text, inspect
    with engine.connect() as conn:
        user_cols = [c["name"] for c in inspect(engine).get_columns("users")]
        if "language" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN language VARCHAR(4) DEFAULT 'fa'"))
            logger.info("Migrated: added language column")

        tx_cols = [c["name"] for c in inspect(engine).get_columns("transactions")]
        if "receipt_number" not in tx_cols:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN receipt_number VARCHAR(128)"))
            logger.info("Migrated: added receipt_number column")

        plan_cols = [c["name"] for c in inspect(engine).get_columns("plans")]
        if "mikrotik_profile" not in plan_cols:
            conn.execute(text("ALTER TABLE plans ADD COLUMN mikrotik_profile VARCHAR(64)"))
            logger.info("Migrated: added mikrotik_profile column to plans")
        if "is_test" not in plan_cols:
            conn.execute(text("ALTER TABLE plans ADD COLUMN is_test BOOLEAN DEFAULT 0"))
            logger.info("Migrated: added is_test column to plans")

        conn.commit()


# ── Active conversation tracking (per user) ───────────────────────────────────
_bank_conv_active: dict[int, bool] = {}    # user waiting to send bank receipt (order)
_topup_conv_active: dict[int, str] = {}    # user waiting to send bank receipt (topup)


async def main_callback(update: Update, context):
    query = update.callback_query
    data = query.data

    routes = {
        "start": _back_to_start,
        "plans": show_plans,
        "my_orders": my_orders,
        "renew": show_renewal_accounts,
        "usage": show_usage_accounts,
        "wallet": wallet_menu,
        "help": _help_inline,
        "reviews": show_reviews,
        "choose_lang": choose_language_callback,
        "admin_stats": admin_stats,
        "admin_pending": admin_pending_payments,
    }

    if data in routes:
        await routes[data](update, context)
    elif data.startswith("setlang_"):
        await set_language_callback(update, context)
    elif data.startswith("plan_"):
        await plan_detail(update, context)
    elif data.startswith("order_"):
        await order_detail(update, context)
    elif data.startswith("renew_acct_"):
        await renewal_account_selected(update, context)
    elif data.startswith("renew_plan_"):
        await renewal_plan_selected(update, context)
    elif data.startswith("usage_acct_"):
        await show_account_usage(update, context)
    elif data.startswith("pay_stripe_"):
        await pay_stripe(update, context)
    elif data.startswith("check_stripe_"):
        await check_stripe(update, context)
    elif data.startswith("pay_trc20_"):
        await pay_trc20(update, context)
    elif data.startswith("check_trc20_"):
        await check_trc20(update, context)
    elif data.startswith("pay_erc20_"):
        await pay_erc20(update, context)
    elif data.startswith("check_erc20_"):
        await check_erc20(update, context)
    elif data.startswith("get_test_"):
        await activate_test_plan(update, context)
    elif data.startswith("pay_wallet_"):
        await pay_wallet(update, context)
    elif data.startswith("pay_bank_"):
        await _start_bank_conv(update, context)
    elif data == "topup_trc20":
        await topup_trc20_start(update, context)
    elif data == "topup_erc20":
        await topup_erc20_start(update, context)
    elif data == "topup_bank":
        await _start_bank_topup_conv(update, context)
    elif data == "topup_check_trc20":
        await topup_check_trc20(update, context)
    elif data == "topup_check_erc20":
        await topup_check_erc20(update, context)
    elif data.startswith("approve_bank_"):
        await _start_admin_approve(update, context, "bank")
    elif data.startswith("approve_topup_"):
        await _start_admin_approve(update, context, "topup")
    elif data.startswith("reject_bank_"):
        await reject_bank_payment(update, context)
    elif data.startswith("reject_topup_"):
        await reject_topup(update, context)


async def _back_to_start(update: Update, context):
    from handlers.start import _main_menu_keyboard
    from utils.helpers import get_user_language
    from utils.i18n import t
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    await query.edit_message_text(
        t("welcome", lang, name=update.effective_user.first_name),
        reply_markup=_main_menu_keyboard(lang),
        parse_mode="Markdown",
    )


async def _help_inline(update: Update, context):
    from utils.helpers import get_user_language
    from utils.i18n import t
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    await query.edit_message_text(t("help_text", lang), parse_mode="Markdown")


# ── User conversation bootstraps ──────────────────────────────────────────────

async def _start_bank_conv(update: Update, context):
    await pay_bank(update, context)
    _bank_conv_active[update.effective_user.id] = True


async def _start_bank_topup_conv(update: Update, context):
    await topup_bank_start(update, context)
    _topup_conv_active[update.effective_user.id] = "bank"


# ── Admin approval bootstrap ──────────────────────────────────────────────────

async def _start_admin_approve(update: Update, context, kind: str):
    if kind == "bank":
        await start_approve_bank(update, context)
    else:
        await start_approve_topup(update, context)
    # Mark this admin as being in an approval conversation
    _pending_approvals.setdefault(update.effective_user.id, {})


# ── Text and media routers ────────────────────────────────────────────────────

async def text_router(update: Update, context):
    uid = update.effective_user.id

    # Admin approval conversation takes priority for admin users
    if uid in _pending_approvals and _pending_approvals[uid]:
        state = _pending_approvals[uid].get("state")
        if state == "amount":
            result = await approve_amount_received(update, context)
            if result == APPROVE_WAITING_RECEIPT:
                _pending_approvals[uid]["state"] = "receipt"
            elif result == ConversationHandler.END or result is None:
                _pending_approvals.pop(uid, None)
        elif state == "receipt":
            result = await approve_receipt_received(update, context)
            if result == ConversationHandler.END or result is None:
                _pending_approvals.pop(uid, None)


async def receipt_router(update: Update, context):
    uid = update.effective_user.id
    if uid in _bank_conv_active:
        await receive_receipt(update, context)
        _bank_conv_active.pop(uid, None)
    elif uid in _topup_conv_active and _topup_conv_active[uid] == "bank":
        await topup_bank_receipt(update, context)
        _topup_conv_active.pop(uid, None)


def main():
    init_db()
    _run_migrations()
    seed_plans()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("plans", lambda u, c: show_plans(u, c)))
    app.add_handler(CommandHandler("orders", lambda u, c: my_orders(u, c)))
    app.add_handler(CommandHandler("wallet", lambda u, c: wallet_menu(u, c)))
    app.add_handler(CommandHandler("admin", admin_menu))

    app.add_handler(CallbackQueryHandler(main_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receipt_router))

    app.job_queue.run_repeating(lambda ctx: check_and_expire_orders(), interval=600, first=30)

    logger.info("Bot starting…")
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
