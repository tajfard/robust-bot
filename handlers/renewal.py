"""Renewal flow — let users extend or re-plan their existing accounts."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.db import get_db
from database.models import Order, OrderStatus, Plan
from services.plans import fmt_plan_button, fmt_bandwidth, fmt_duration, fmt_price
from utils.helpers import get_user_language
from utils.i18n import t


async def show_renewal_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                Order.status.in_([OrderStatus.ACTIVE, OrderStatus.EXPIRED, OrderStatus.PAID]),
                Plan.is_test.is_(False),
                Order.vpn_username.isnot(None),
            )
            .order_by(Order.expires_at.desc())
            .all()
        )
        order_items = [
            (o.id, o.vpn_username, o.plan.name, o.status.value, o.expires_at)
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
                t("no_renewable", lang),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t("btn_back", lang), callback_data="start")
                ]]),
            )
        return

    status_emoji = {"active": "✅", "expired": "❌", "paid": "💳"}
    keyboard = []
    for oid, uname, plan_name, status, expires in order_items:
        emoji = status_emoji.get(status, "📦")
        exp_str = expires.strftime("%Y-%m-%d") if expires else "?"
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {uname} ({plan_name}) — {exp_str}",
            callback_data=f"renew_acct_{oid}",
        )])
    keyboard.append([InlineKeyboardButton(t("btn_back", lang), callback_data="start")])

    if query:
        await query.answer()
        await query.edit_message_text(
            t("renew_title", lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )


async def renewal_account_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User tapped an account — show plan selection for renewal."""
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[2])
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    with get_db() as db:
        order = db.get(Order, order_id)
        if not order or order.vpn_username is None:
            await query.edit_message_text(t("order_not_found", lang))
            return
        current_plan_id = order.plan_id
        vpn_username = order.vpn_username
        vpn_password = order.vpn_password or ""

        plans = (
            db.query(Plan)
            .filter(Plan.is_active.is_(True), Plan.is_test.is_(False))
            .all()
        )
        plan_data = [(p.id, fmt_plan_button(p, lang), p.id == current_plan_id) for p in plans]

    context.user_data["renewal_info"] = {
        "username": vpn_username,
        "password": vpn_password,
        "source_order_id": order_id,
    }

    keyboard = []
    for pid, label, is_current in plan_data:
        prefix = "✅ " if is_current else ""
        keyboard.append([InlineKeyboardButton(
            f"{prefix}{label}",
            callback_data=f"renew_plan_{pid}",
        )])
    keyboard.append([InlineKeyboardButton(t("btn_back", lang), callback_data="renew")])

    await query.edit_message_text(
        t("renew_select_plan", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def renewal_plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a plan — show payment methods (same as regular purchase)."""
    query = update.callback_query
    await query.answer()
    plan_id = int(query.data.split("_")[2])
    lang = get_user_language(update.effective_user.id)

    # renewal_info must already be in context.user_data from renewal_account_selected
    if "renewal_info" not in context.user_data:
        await query.edit_message_text(t("order_not_found", lang))
        return

    with get_db() as db:
        plan = db.get(Plan, plan_id)
        if not plan:
            await query.edit_message_text(t("plan_not_found", lang))
            return
        bw = fmt_bandwidth(plan.bandwidth_gb, lang)
        dur = fmt_duration(plan.duration_days, lang)
        price = fmt_price(plan.price_usd, lang)
        conn = plan.simultaneous_connections

    keyboard = [
        [InlineKeyboardButton(t("btn_pay_stripe", lang), callback_data=f"pay_stripe_{plan_id}")],
        [InlineKeyboardButton(t("btn_pay_trc20", lang),  callback_data=f"pay_trc20_{plan_id}")],
        [InlineKeyboardButton(t("btn_pay_erc20", lang),  callback_data=f"pay_erc20_{plan_id}")],
        [InlineKeyboardButton(t("btn_pay_wallet", lang), callback_data=f"pay_wallet_{plan_id}")],
        [InlineKeyboardButton(t("btn_pay_bank", lang),   callback_data=f"pay_bank_{plan_id}")],
        [InlineKeyboardButton(t("btn_back", lang),       callback_data="renew")],
    ]
    await query.edit_message_text(
        t("plan_detail_paid", lang, bw=bw, dur=dur, price=price, conn=conn),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
