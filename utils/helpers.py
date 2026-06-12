import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from database.db import get_db
from database.models import User
from utils.i18n import t
from config import VPN_CONFIG_FILE


async def send_vpn_config(bot, chat_id: int):
    """Send the .ovpn config file to the user after successful order activation."""
    if not VPN_CONFIG_FILE or not os.path.exists(VPN_CONFIG_FILE):
        return
    with open(VPN_CONFIG_FILE, "rb") as f:
        await bot.send_document(chat_id=chat_id, document=f, filename=os.path.basename(VPN_CONFIG_FILE))


def credentials_keyboard(username: str, password: str, lang: str) -> InlineKeyboardMarkup:
    """Inline keyboard with one-tap copy buttons and a back-to-menu button."""
    u_label = "📋 کپی نام کاربری" if lang == "fa" else "📋 Copy Username"
    p_label = "📋 کپی رمز عبور" if lang == "fa" else "📋 Copy Password"
    home_label = "🏠 منوی اصلی" if lang == "fa" else "🏠 Main Menu"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(u_label, copy_text=CopyTextButton(text=username)),
            InlineKeyboardButton(p_label, copy_text=CopyTextButton(text=password)),
        ],
        [InlineKeyboardButton(home_label, callback_data="start")],
    ])


def get_or_create_user(telegram_id: int, username: str, full_name: str, language: str = "fa") -> User:
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                language=language,
            )
            db.add(user)
            db.flush()
        # Eagerly touch all scalar attributes so they survive session close
        # (expire_on_commit=False keeps committed values, but new objects need this)
        _ = user.id, user.telegram_id, user.language, user.wallet_balance, user.is_banned
        return user


def get_user_language(telegram_id: int) -> str:
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        return (user.language or "fa") if user else "fa"


def set_user_language(telegram_id: int, lang: str):
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.language = lang
            db.add(user)


def format_order_info(order, lang: str = "fa") -> str:
    status_emoji = {
        "pending": "⏳",
        "paid": "💳",
        "active": "✅",
        "expired": "❌",
        "cancelled": "🚫",
    }
    emoji = status_emoji.get(order.status.value, "❓")
    if lang == "fa":
        lines = [f"{emoji} *سفارش #{order.id}*", f"پلن: {order.plan.name}", f"وضعیت: {order.status.value.upper()}"]
        if order.vpn_username:
            lines += [f"نام کاربری: `{order.vpn_username}`", f"رمز عبور: `{order.vpn_password}`"]
        if order.expires_at:
            lines.append(f"انقضا: {order.expires_at.strftime('%Y-%m-%d %H:%M')} UTC")
    else:
        lines = [f"{emoji} *Order #{order.id}*", f"Plan: {order.plan.name}", f"Status: {order.status.value.upper()}"]
        if order.vpn_username:
            lines += [f"Username: `{order.vpn_username}`", f"Password: `{order.vpn_password}`"]
        if order.expires_at:
            lines.append(f"Expires: {order.expires_at.strftime('%Y-%m-%d %H:%M')} UTC")
    return "\n".join(lines)
