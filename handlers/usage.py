"""Account usage handler — shows MikroTik traffic stats for a user's VPN account."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.db import get_db
from database.models import Order, OrderStatus, Plan
from services import mikrotik
from utils.helpers import get_user_language
from utils.i18n import t


def _fmt_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024 ** 3:.2f} GB"


async def show_usage_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    with get_db() as db:
        rows = (
            db.query(Order)
            .join(Order.user)
            .filter_by(telegram_id=tg_user.id)
            .join(Order.plan)
            .filter(
                Order.status == OrderStatus.ACTIVE,
                Plan.is_test.is_(False),
                Order.vpn_username.isnot(None),
            )
            .order_by(Order.expires_at.desc())
            .all()
        )
        order_items = [
            (o.id, o.vpn_username, o.plan.name, o.expires_at)
            for o in rows
        ]

    # Deduplicate: one entry per username (already sorted latest first)
    seen_usernames: set[str] = set()
    unique_items = []
    for item in order_items:
        uname = item[1]
        if uname not in seen_usernames:
            seen_usernames.add(uname)
            unique_items.append(item)
    order_items = unique_items

    if not order_items:
        if query:
            await query.answer()
            await query.edit_message_text(
                t("no_active_accounts", lang),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t("btn_back", lang), callback_data="start")
                ]]),
            )
        return

    keyboard = []
    for oid, uname, plan_name, expires in order_items:
        exp_str = expires.strftime("%Y-%m-%d") if expires else "?"
        keyboard.append([InlineKeyboardButton(
            f"✅ {uname} ({plan_name}) — {exp_str}",
            callback_data=f"usage_acct_{oid}",
        )])
    keyboard.append([InlineKeyboardButton(t("btn_back", lang), callback_data="start")])

    if query:
        await query.answer()
        await query.edit_message_text(
            t("usage_title", lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )


async def show_account_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Query MikroTik and display traffic usage for a specific account."""
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[2])
    lang = get_user_language(update.effective_user.id)

    with get_db() as db:
        order = db.get(Order, order_id)
        if not order or not order.vpn_username:
            await query.edit_message_text(t("order_not_found", lang))
            return
        username = order.vpn_username
        plan_name = order.plan.name
        bandwidth_gb = order.plan.bandwidth_gb
        expires = order.expires_at

    expires_str = expires.strftime("%Y-%m-%d") if expires else "?"
    back_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t("btn_back", lang), callback_data="usage")
    ]])

    try:
        stats = mikrotik.get_user_stats(username)
    except Exception:
        await query.edit_message_text(
            t("usage_unavailable", lang, username=username, plan=plan_name, expires=expires_str),
            reply_markup=back_kb,
            parse_mode="Markdown",
        )
        return

    if not stats.get("found"):
        await query.edit_message_text(
            t("usage_unavailable", lang, username=username, plan=plan_name, expires=expires_str),
            reply_markup=back_kb,
            parse_mode="Markdown",
        )
        return

    bytes_in = stats["bytes_in"]
    bytes_out = stats["bytes_out"]
    total_used = bytes_in + bytes_out
    total_quota = int(bandwidth_gb * 1024 ** 3) if bandwidth_gb else 0

    if total_quota > 0:
        remaining = max(0, total_quota - total_used)
        remaining_str = _fmt_bytes(remaining)
    else:
        remaining_str = "∞" if lang == "en" else "نامحدود"

    await query.edit_message_text(
        t("account_usage", lang,
          username=username,
          plan=plan_name,
          expires=expires_str,
          bytes_in=_fmt_bytes(bytes_in),
          bytes_out=_fmt_bytes(bytes_out),
          total_used=_fmt_bytes(total_used),
          remaining=remaining_str),
        reply_markup=back_kb,
        parse_mode="Markdown",
    )
