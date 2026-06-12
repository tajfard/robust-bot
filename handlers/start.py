from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import get_or_create_user, get_user_language, set_user_language
from utils.i18n import t


def _main_menu_keyboard(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_plans", lang), callback_data="plans")],
        [InlineKeyboardButton(t("btn_renew", lang), callback_data="renew")],
        [
            InlineKeyboardButton(t("btn_wallet", lang), callback_data="wallet"),
            InlineKeyboardButton(t("btn_usage", lang), callback_data="usage"),
        ],
        [
            InlineKeyboardButton(t("btn_support", lang), url="https://t.me/starnetshiraz"),
            InlineKeyboardButton(t("btn_guide", lang), url="https://t.me/robust_vpn"),
        ],
        [InlineKeyboardButton(t("btn_reviews", lang), callback_data="reviews")],
        [InlineKeyboardButton(t("btn_help", lang), callback_data="help")],
        [InlineKeyboardButton(t("btn_language", lang), callback_data="choose_lang")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = get_or_create_user(tg_user.id, tg_user.username or "", tg_user.full_name or "")

    # First-time users get the language picker
    if not user.language:
        await _send_language_picker(update)
        return

    lang = user.language
    await update.message.reply_text(
        t("welcome", lang, name=tg_user.first_name),
        reply_markup=_main_menu_keyboard(lang),
        parse_mode="Markdown",
    )


async def _send_language_picker(update: Update):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
        InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
    ]])
    msg = update.message or update.callback_query.message
    await msg.reply_text(t("choose_language", "fa"), reply_markup=keyboard)


async def choose_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
        InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
    ]])
    await query.edit_message_text(t("choose_language", "fa"), reply_markup=keyboard)


async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.data.split("_")[1]  # setlang_fa → fa
    tg_user = update.effective_user
    set_user_language(tg_user.id, lang)
    await query.answer(t("language_set", lang))
    await query.edit_message_text(
        t("welcome", lang, name=tg_user.first_name),
        reply_markup=_main_menu_keyboard(lang),
        parse_mode="Markdown",
    )


async def show_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update.effective_user.id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "⭐⭐⭐⭐⭐ Google Reviews",
            url="https://share.google/laMHfBr44ULgrRVEv",
        )],
        [InlineKeyboardButton(
            "⭐⭐⭐⭐⭐ Trustpilot",
            url="https://www.trustpilot.com/review/robustvpn.host",
        )],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="start")],
    ])
    await query.edit_message_text(
        t("reviews_title", lang),
        reply_markup=keyboard,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    await update.message.reply_text(t("help_text", lang), parse_mode="Markdown")
