from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.db import get_db
from database.models import Plan, Order, OrderStatus
from services.plans import fmt_plan_button, fmt_bandwidth, fmt_duration, fmt_price, has_used_test_plan
from services.vpn_manager import activate_order
from utils.helpers import get_or_create_user, get_user_language, format_order_info, credentials_keyboard
from utils.i18n import t


async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message if query else update.message
    lang = get_user_language(update.effective_user.id)

    with get_db() as db:
        plans = db.query(Plan).filter(Plan.is_active == True).all()
        plan_data = [(p.id, fmt_plan_button(p, lang)) for p in plans]

    if not plan_data:
        text = t("no_plans", lang)
        if query:
            await query.answer()
            await query.edit_message_text(text)
        else:
            await message.reply_text(text)
        return

    keyboard = [[InlineKeyboardButton(label, callback_data=f"plan_{pid}")] for pid, label in plan_data]
    keyboard.append([InlineKeyboardButton(t("btn_back", lang), callback_data="start")])

    text = t("plans_title", lang)
    markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.answer()
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


async def plan_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = int(query.data.split("_")[1])
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)
    context.user_data.pop("renewal_info", None)  # clear any leftover renewal context

    with get_db() as db:
        plan = db.get(Plan, plan_id)
        if not plan:
            await query.edit_message_text(t("plan_not_found", lang))
            return
        bw = fmt_bandwidth(plan.bandwidth_gb, lang)
        dur = fmt_duration(plan.duration_days, lang)
        price = fmt_price(plan.price_usd, lang)
        is_test = plan.is_test
        conn = plan.simultaneous_connections

    back = InlineKeyboardButton(t("btn_back_to_plans", lang), callback_data="plans")

    if is_test:
        text = t("plan_detail_test", lang, bw=bw, dur=dur)
        keyboard = [
            [InlineKeyboardButton(t("btn_get_test", lang), callback_data=f"get_test_{plan_id}")],
            [back],
        ]
    else:
        text = t("plan_detail_paid", lang, bw=bw, dur=dur, price=price, conn=conn)
        keyboard = [
            [InlineKeyboardButton(t("btn_pay_stripe", lang), callback_data=f"pay_stripe_{plan_id}")],
            [InlineKeyboardButton(t("btn_pay_trc20", lang),  callback_data=f"pay_trc20_{plan_id}")],
            [InlineKeyboardButton(t("btn_pay_erc20", lang),  callback_data=f"pay_erc20_{plan_id}")],
            [InlineKeyboardButton(t("btn_pay_wallet", lang), callback_data=f"pay_wallet_{plan_id}")],
            [InlineKeyboardButton(t("btn_pay_bank", lang),   callback_data=f"pay_bank_{plan_id}")],
            [back],
        ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def activate_test_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = int(query.data.split("_")[2])
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)

    # Look up the user's DB id
    with get_db() as db:
        from database.models import User
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        if not user:
            await query.edit_message_text(t("plan_not_found", lang))
            return
        user_id = user.id

    if has_used_test_plan(user_id, plan_id):
        await query.edit_message_text(
            t("test_already_used", lang),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("btn_back_to_plans", lang), callback_data="plans")
            ]]),
            parse_mode="Markdown",
        )
        return

    # Create order then activate; cancel it if MikroTik fails so the user can retry
    from database.models import OrderStatus, PaymentMethod
    with get_db() as db:
        order = Order(
            user_id=user_id,
            plan_id=plan_id,
            status=OrderStatus.PENDING,
            payment_method=PaymentMethod.WALLET,
            amount_paid=0.0,
        )
        db.add(order)
        db.flush()
        order_id = order.id

    try:
        activated = activate_order(order_id)
    except Exception as e:
        with get_db() as db:
            order = db.get(Order, order_id)
            if order:
                order.status = OrderStatus.CANCELLED
        await query.edit_message_text(
            "⚠️ خطا در اتصال به سرور VPN. لطفاً دوباره امتحان کنید.\n\nVPN server error. Please try again.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("btn_back_to_plans", lang), callback_data="plans")
            ]]),
        )
        return

    await query.edit_message_text(
        t("test_activated", lang,
          username=activated.vpn_username,
          password=activated.vpn_password,
          expires=activated.expires_at.strftime("%Y-%m-%d")),
        reply_markup=credentials_keyboard(activated.vpn_username, activated.vpn_password, lang),
        parse_mode="Markdown",
    )


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message if query else update.message
    tg_user = update.effective_user
    lang = get_user_language(tg_user.id)
    get_or_create_user(tg_user.id, tg_user.username or "", tg_user.full_name or "")

    with get_db() as db:
        rows = (
            db.query(Order)
            .join(Order.user)
            .filter_by(telegram_id=tg_user.id)
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )
        # Extract everything needed while session is still open — avoids DetachedInstanceError
        order_items = [(o.id, o.plan.name, o.status.value) for o in rows]

    if not order_items:
        text = t("no_orders", lang)
        if query:
            await query.answer()
            await query.edit_message_text(text)
        else:
            await message.reply_text(text)
        return

    status_emoji = {"pending": "⏳", "paid": "💳", "active": "✅", "expired": "❌", "cancelled": "🚫"}
    lines = [t("orders_title", lang)]
    for oid, plan_name, status in order_items:
        emoji = status_emoji.get(status, "❓")
        lines.append(f"{emoji} #{oid} — {plan_name} ({status})")

    keyboard = [[InlineKeyboardButton(f"#{oid} {plan_name}", callback_data=f"order_{oid}")] for oid, plan_name, _ in order_items]
    keyboard.append([InlineKeyboardButton(t("btn_back", lang), callback_data="start")])

    text = "\n".join(lines)
    if query:
        await query.answer()
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[1])
    lang = get_user_language(update.effective_user.id)

    with get_db() as db:
        order = db.get(Order, order_id)
        if not order:
            await query.edit_message_text(t("order_not_found", lang))
            return
        text = format_order_info(order, lang)  # called inside session — plan lazy-loads safely

    keyboard = [[InlineKeyboardButton(t("btn_back", lang), callback_data="my_orders")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
