"""All UI strings in Persian (fa) and English (en)."""

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Language selection ───────────────────────────────────────────────────
    "choose_language": {
        "fa": "🌐 زبان مورد نظر خود را انتخاب کنید:\nPlease choose your language:",
        "en": "🌐 Please choose your language:\nلطفاً زبان خود را انتخاب کنید:",
    },
    "language_set": {
        "fa": "✅ زبان فارسی انتخاب شد.",
        "en": "✅ Language set to English.",
    },
    "btn_fa": {"fa": "🇮🇷 فارسی", "en": "🇮🇷 فارسی"},
    "btn_en": {"fa": "🇬🇧 English", "en": "🇬🇧 English"},

    # ── Main menu ────────────────────────────────────────────────────────────
    "welcome": {
        "fa": "👋 خوش آمدید، *{name}*!\n\nبرای خرید آی پی ایران یکی از گزینه‌ها را انتخاب کنید:",
        "en": "👋 Welcome, *{name}*!\n\nSelect an option to get your Iran VPN:",
    },
    "btn_plans": {"fa": "📦 پلن‌های VPN", "en": "📦 VPN Plans"},
    "btn_orders": {"fa": "💼 سفارش‌های من", "en": "💼 My Orders"},
    "btn_renew": {"fa": "🔄 تمدید اکانت", "en": "🔄 Renew Account"},
    "btn_wallet": {"fa": "👛 کیف پول من", "en": "👛 My Wallet"},
    "btn_usage": {"fa": "📊 مشاهده مانده اکانت", "en": "📊 Account Usage"},
    "btn_help": {"fa": "❓ راهنما", "en": "❓ Help"},
    "btn_language": {"fa": "🌐 تغییر زبان", "en": "🌐 Change Language"},
    "btn_support": {"fa": "📞 پشتیبانی", "en": "📞 Support"},
    "btn_guide": {"fa": "📖 راهنمای اتصال", "en": "📖 Connection Guide"},
    "btn_reviews": {"fa": "⭐⭐⭐⭐⭐ مشاهده نظرات", "en": "⭐⭐⭐⭐⭐ View Reviews"},
    "reviews_title": {
        "fa": "نظرات ما را در پلتفرم مورد نظر مشاهده کنید:",
        "en": "Read our reviews on your preferred platform:",
    },
    "btn_back": {"fa": "🔙 بازگشت", "en": "🔙 Back"},
    "btn_back_to_plans": {"fa": "🔙 بازگشت به پلن‌ها", "en": "🔙 Back to Plans"},

    # ── Help ─────────────────────────────────────────────────────────────────
    "help_text": {
        "fa": (
            "*دستورات موجود:*\n"
            "/start — منوی اصلی\n"
            "/plans — مشاهده پلن‌های VPN\n"
            "/orders — سفارش‌های من\n"
            "/wallet — کیف پول و شارژ\n"
            "/help — این پیام\n\n"
            "برای پشتیبانی با ادمین تماس بگیرید."
        ),
        "en": (
            "*Available commands:*\n"
            "/start — Main menu\n"
            "/plans — Browse VPN plans\n"
            "/orders — My orders\n"
            "/wallet — Wallet & top-up\n"
            "/help — This message\n\n"
            "For support, contact the admin."
        ),
    },

    # ── Plans ────────────────────────────────────────────────────────────────
    "plans_title": {
        "fa": "📦 *پلن‌های VPN*\nیک پلن انتخاب کنید:",
        "en": "📦 *VPN Plans*\nChoose a plan:",
    },
    "no_plans": {
        "fa": "در حال حاضر پلنی موجود نیست.",
        "en": "No plans available at the moment.",
    },
    "plan_detail_paid": {
        "fa": (
            "*{bw} / {dur}*\n\n"
            "💰 قیمت: *{price}*\n"
            "🔗 اتصال همزمان: *{conn}*\n\n"
            "روش پرداخت را انتخاب کنید:"
        ),
        "en": (
            "*{bw} / {dur}*\n\n"
            "💰 Price: *{price}*\n"
            "🔗 Connections: *{conn}*\n\n"
            "Choose payment method:"
        ),
    },
    "plan_detail_test": {
        "fa": (
            "🆓 *اکانت تست*\n\n"
            "📶 حجم: *{bw}*\n"
            "📅 مدت: *{dur}*\n"
            "💰 رایگان — فقط یک بار برای هر کاربر\n\n"
            "برای دریافت اکانت تست دکمه زیر را بزنید:"
        ),
        "en": (
            "🆓 *Test Account*\n\n"
            "📶 Bandwidth: *{bw}*\n"
            "📅 Duration: *{dur}*\n"
            "💰 Free — once per user\n\n"
            "Tap the button below to activate your test account:"
        ),
    },
    "btn_get_test": {"fa": "🆓 دریافت اکانت تست", "en": "🆓 Get Test Account"},
    "test_already_used": {
        "fa": "❌ شما قبلاً از اکانت تست استفاده کرده‌اید.",
        "en": "❌ You have already used your free test account.",
    },
    "test_activated": {
        "fa": (
            "✅ *اکانت تست فعال شد!*\n\n"
            "🔐 *نام کاربری:* `{username}`\n"
            "🔑 *رمز عبور:* `{password}`\n"
            "📅 انقضا: {expires}"
        ),
        "en": (
            "✅ *Test account activated!*\n\n"
            "🔐 *Username:* `{username}`\n"
            "🔑 *Password:* `{password}`\n"
            "📅 Expires: {expires}"
        ),
    },
    "plan_not_found": {"fa": "پلن پیدا نشد.", "en": "Plan not found."},

    # ── Payment method buttons ───────────────────────────────────────────────
    "btn_pay_stripe": {"fa": "💳 پرداخت با کارت (Stripe)", "en": "💳 Pay by Card (Stripe)"},
    "btn_pay_trc20": {"fa": "🪙 USDT TRC20 (ترون)", "en": "🪙 USDT TRC20 (Tron)"},
    "btn_pay_erc20": {"fa": "🦊 USDT ERC20 (اتریوم)", "en": "🦊 USDT ERC20 (Ethereum)"},
    "btn_pay_wallet": {"fa": "👛 پرداخت از کیف پول", "en": "👛 Use Wallet Balance"},
    "btn_pay_bank": {"fa": "🏦 انتقال بانکی", "en": "🏦 Bank Transfer"},

    # ── Stripe ───────────────────────────────────────────────────────────────
    "stripe_instruction": {
        "fa": "💳 *پرداخت با کارت (Stripe)*\n\nمبلغ: *${amount}*\n\nروی دکمه زیر کلیک کرده و پرداخت را تکمیل کنید.",
        "en": "💳 *Card Payment (Stripe)*\n\nAmount: *${amount}*\n\nClick the button below to complete payment.",
    },
    "btn_pay_now": {"fa": "💳 پرداخت", "en": "💳 Pay Now"},
    "btn_stripe_check": {"fa": "✅ پرداخت کردم — بررسی", "en": "✅ I've Paid — Check"},
    "stripe_not_paid_yet": {
        "fa": "⏳ پرداخت هنوز تأیید نشده. چند ثانیه صبر کرده دوباره امتحان کنید.",
        "en": "⏳ Payment not confirmed yet. Wait a few seconds and try again.",
    },
    "stripe_webhook_note": {
        "fa": "⏳ پرداخت شما از طریق webhook بررسی می‌شود.\nبه محض تأیید، اکانت شما فعال خواهد شد.\n\n/orders را بررسی کنید.",
        "en": "⏳ Payment is verified via Stripe webhook.\nYour account will activate automatically once confirmed.\n\nCheck /orders for status.",
    },

    # ── TRC20 ────────────────────────────────────────────────────────────────
    "trc20_instruction": {
        "fa": (
            "🪙 *پرداخت USDT TRC20*\n\n"
            "دقیقاً *{amount} USDT* (شبکه TRC20) به آدرس زیر ارسال کنید:\n\n"
            "`{address}`\n\n"
            "⚠️ فقط از شبکه *ترون (TRC20)* ارسال کنید.\n\n"
            "پس از ارسال، *هش تراکنش (TX Hash)* خود را اینجا ارسال کنید."
        ),
        "en": (
            "🪙 *USDT TRC20 Payment*\n\n"
            "Send exactly *{amount} USDT* (TRC20 network) to:\n\n"
            "`{address}`\n\n"
            "⚠️ Only send USDT on the *Tron (TRC20)* network.\n\n"
            "After sending, paste your *TX Hash* here in the chat."
        ),
    },
    "btn_sent_check": {"fa": "✅ ارسال کردم — بررسی", "en": "✅ I've Sent — Check"},
    "btn_cancel": {"fa": "❌ انصراف", "en": "❌ Cancel"},

    # ── ERC20 ────────────────────────────────────────────────────────────────
    "erc20_instruction": {
        "fa": (
            "🦊 *پرداخت USDT ERC20*\n\n"
            "دقیقاً *{amount} USDT* (شبکه اتریوم ERC20) به آدرس زیر ارسال کنید:\n\n"
            "`{address}`\n\n"
            "⚠️ فقط از شبکه *اتریوم (ERC20)* ارسال کنید.\n"
            "کارمزد گس به عهده شماست.\n\n"
            "پس از ارسال، *هش تراکنش (TX Hash)* خود را اینجا ارسال کنید."
        ),
        "en": (
            "🦊 *USDT ERC20 Payment*\n\n"
            "Send exactly *{amount} USDT* (Ethereum ERC20) to:\n\n"
            "`{address}`\n\n"
            "⚠️ Only send USDT on the *Ethereum (ERC20)* network.\n"
            "Gas fees are your responsibility.\n\n"
            "After sending, paste your *TX Hash* here in the chat."
        ),
    },

    # ── Wallet payment ───────────────────────────────────────────────────────
    "wallet_insufficient": {
        "fa": (
            "❌ موجودی کیف پول کافی نیست.\n\n"
            "نیاز: *{required}*\n"
            "موجودی شما: *{balance}*\n\n"
            "از /wallet برای شارژ استفاده کنید."
        ),
        "en": (
            "❌ Insufficient wallet balance.\n\n"
            "Required: *{required}*\n"
            "Your balance: *{balance}*\n\n"
            "Top up via /wallet."
        ),
    },

    # ── Bank transfer ────────────────────────────────────────────────────────
    "bank_instruction": {
        "fa": (
            "🏦 *انتقال بانکی*\n\n"
            "معادل *${amount}* به حساب زیر واریز کنید:\n\n"
            "🏦 بانک: *{bank}*\n"
            "💳 شماره کارت: `{card}`\n"
            "👤 نام صاحب حساب: *{name}*\n\n"
            "پس از واریز، عکس یا اسکرین‌شات رسید را ارسال کنید."
        ),
        "en": (
            "🏦 *Bank Transfer*\n\n"
            "Transfer the equivalent of *${amount}* to:\n\n"
            "🏦 Bank: *{bank}*\n"
            "💳 Card: `{card}`\n"
            "👤 Account name: *{name}*\n\n"
            "After transfer, send a photo/screenshot of your receipt."
        ),
    },
    "send_receipt": {
        "fa": "لطفاً عکس یا فایل رسید پرداخت را ارسال کنید.",
        "en": "Please send a photo or file of your receipt.",
    },
    "receipt_received": {
        "fa": "✅ رسید دریافت شد. ادمین بررسی کرده و اکانت شما را فعال خواهد کرد.",
        "en": "✅ Receipt received. An admin will review and activate your account shortly.",
    },

    # ── Payment confirmed (VPN credentials) ──────────────────────────────────
    "payment_confirmed": {
        "fa": (
            "✅ *پرداخت تأیید شد!*\n\n"
            "🔐 *نام کاربری:* `{username}`\n"
            "🔑 *رمز عبور:* `{password}`\n"
            "📅 انقضا: {expires}\n\n"
            "TX: `{txhash}`"
        ),
        "en": (
            "✅ *Payment confirmed!*\n\n"
            "🔐 *Username:* `{username}`\n"
            "🔑 *Password:* `{password}`\n"
            "📅 Expires: {expires}\n\n"
            "TX: `{txhash}`"
        ),
    },
    "wallet_activated": {
        "fa": (
            "✅ *سفارش از کیف پول فعال شد!*\n\n"
            "🔐 *نام کاربری:* `{username}`\n"
            "🔑 *رمز عبور:* `{password}`\n"
            "📅 انقضا: {expires}"
        ),
        "en": (
            "✅ *Order activated via wallet!*\n\n"
            "🔐 *Username:* `{username}`\n"
            "🔑 *Password:* `{password}`\n"
            "📅 Expires: {expires}"
        ),
    },
    "invalid_tx_hash": {
        "fa": "❌ هش تراکنش نامعتبر است. لطفاً TX Hash را از کیف پول یا اکسپلورر کپی کرده و ارسال کنید.",
        "en": "❌ Invalid TX hash. Please copy the TX Hash from your wallet or blockchain explorer and send it here.",
    },
    "btn_check_again": {"fa": "🔄 همین هش را دوباره بررسی کن", "en": "🔄 Check This Hash Again"},
    "btn_enter_new_hash": {"fa": "✏️ هش جدید وارد کن", "en": "✏️ Enter New Hash"},
    "retry_hash_prompt": {
        "fa": "لطفاً TX Hash تراکنش خود را اینجا ارسال کنید:",
        "en": "Please paste your TX Hash here:",
    },
    "tx_not_found": {
        "fa": "تراکنشی پیدا نشد. چند دقیقه صبر کرده دوباره امتحان کنید.",
        "en": "No matching transaction found yet. Try again in a minute.",
    },
    "tx_already_used": {
        "fa": "⚠️ این تراکنش قبلاً استفاده شده است. اگر تراکنش جدیدی ارسال کرده‌اید، چند دقیقه صبر کنید.",
        "en": "⚠️ This transaction was already used. If you sent a new one, please wait a few minutes.",
    },
    "overpayment_credited": {
        "fa": "💡 مبلغ اضافی *{excess}* به کیف پول شما واریز شد. موجودی: *{balance}*",
        "en": "💡 Overpayment of *{excess}* credited to your wallet. Balance: *{balance}*",
    },
    "order_not_found": {"fa": "سفارش پیدا نشد.", "en": "Order not found or already processed."},

    # ── Orders ───────────────────────────────────────────────────────────────
    "no_orders": {
        "fa": "هنوز سفارشی ندارید. از /plans شروع کنید.",
        "en": "You have no orders yet. Browse /plans to get started.",
    },
    "orders_title": {"fa": "*سفارش‌های شما:*\n", "en": "*Your Orders:*\n"},

    # ── Wallet ───────────────────────────────────────────────────────────────
    "wallet_menu": {
        "fa": "👛 *کیف پول شما*\n\nموجودی: *{balance}*\n\nروش شارژ را انتخاب کنید:",
        "en": "👛 *Your Wallet*\n\nBalance: *{balance}*\n\nChoose top-up method:",
    },
    "btn_topup_stripe": {"fa": "💳 شارژ با کارت (Stripe)", "en": "💳 Top-up via Card (Stripe)"},
    "btn_topup_trc20": {"fa": "🪙 شارژ با USDT TRC20", "en": "🪙 Top-up via USDT TRC20"},
    "btn_topup_erc20": {"fa": "🦊 شارژ با USDT ERC20", "en": "🦊 Top-up via USDT ERC20"},
    "btn_topup_bank": {"fa": "🏦 شارژ با انتقال بانکی", "en": "🏦 Top-up via Bank Transfer"},
    "ask_topup_amount": {
        "fa": "مبلغ شارژ (به دلار) را وارد کنید (مثلاً `20`):",
        "en": "Enter the amount in USD to top up (e.g. `20`):",
    },
    "invalid_amount": {
        "fa": "مبلغ نامعتبر است. یک عدد مثبت مثل `20` وارد کنید.",
        "en": "Invalid amount. Please enter a positive number like `20`.",
    },
    "topup_stripe_select_amount": {
        "fa": "💳 *شارژ کیف پول با Stripe*\n\nمبلغ مورد نظر را انتخاب کنید:",
        "en": "💳 *Stripe Wallet Top-up*\n\nSelect an amount to add to your wallet:",
    },
    "topup_stripe_instruction": {
        "fa": "💳 *شارژ کیف پول با Stripe*\n\nمبلغ: *${amount}*\n\nروی دکمه زیر کلیک کرده پرداخت را تکمیل کنید.",
        "en": "💳 *Stripe Wallet Top-up*\n\nAmount: *${amount}*\n\nClick below to complete payment.",
    },
    "wallet_topup_trc20": {
        "fa": (
            "🪙 *شارژ کیف پول با USDT TRC20*\n\n"
            "هر مقداری USDT (شبکه TRC20) به آدرس زیر ارسال کنید:\n\n"
            "`{address}`\n\n"
            "⚠️ فقط از شبکه *ترون (TRC20)* ارسال کنید.\n\n"
            "پس از ارسال، *هش تراکنش (TX Hash)* خود را اینجا ارسال کنید."
        ),
        "en": (
            "🪙 *USDT TRC20 Wallet Top-up*\n\n"
            "Send any amount of USDT (TRC20 network) to:\n\n"
            "`{address}`\n\n"
            "⚠️ Only send USDT on the *Tron (TRC20)* network.\n\n"
            "After sending, paste your *TX Hash* here in the chat."
        ),
    },
    "wallet_topup_erc20": {
        "fa": (
            "🦊 *شارژ کیف پول با USDT ERC20*\n\n"
            "هر مقداری USDT (شبکه اتریوم ERC20) به آدرس زیر ارسال کنید:\n\n"
            "`{address}`\n\n"
            "⚠️ فقط از شبکه *اتریوم (ERC20)* ارسال کنید.\n\n"
            "پس از ارسال، *هش تراکنش (TX Hash)* خود را اینجا ارسال کنید."
        ),
        "en": (
            "🦊 *USDT ERC20 Wallet Top-up*\n\n"
            "Send any amount of USDT (Ethereum ERC20 network) to:\n\n"
            "`{address}`\n\n"
            "⚠️ Only send USDT on the *Ethereum (ERC20)* network.\n\n"
            "After sending, paste your *TX Hash* here in the chat."
        ),
    },
    "wallet_topup_bank": {
        "fa": (
            "🏦 *شارژ کیف پول با انتقال بانکی*\n\n"
            "مبلغ مورد نظر را به حساب زیر واریز کنید:\n\n"
            "🏦 بانک: *{bank}*\n"
            "💳 کارت: `{card}`\n"
            "👤 نام: *{name}*\n\n"
            "پس از واریز، عکس رسید را ارسال کنید."
        ),
        "en": (
            "🏦 *Bank Transfer Wallet Top-up*\n\n"
            "Transfer any amount to:\n\n"
            "🏦 Bank: *{bank}*\n"
            "💳 Card: `{card}`\n"
            "👤 Name: *{name}*\n\n"
            "After transfer, send a photo of your receipt."
        ),
    },
    "wallet_topped_up": {
        "fa": "✅ *کیف پول شارژ شد!*\nافزوده شد: *{amount}*\nموجودی جدید: *{balance}*\nTX: `{txhash}`",
        "en": "✅ *Wallet topped up!*\nAdded: *{amount}*\nNew balance: *{balance}*\nTX: `{txhash}`",
    },
    "wallet_topup_pending": {
        "fa": "✅ رسید دریافت شد. ادمین بررسی کرده و کیف پول شما را شارژ خواهد کرد.",
        "en": "✅ Receipt received. Admin will review and credit your wallet shortly.",
    },

    # ── Admin notifications to user ──────────────────────────────────────────
    "bank_approved": {
        "fa": (
            "✅ *انتقال بانکی شما تأیید شد!*\n\n"
            "🔐 *نام کاربری:* `{username}`\n"
            "🔑 *رمز عبور:* `{password}`\n"
            "📅 انقضا: {expires}"
        ),
        "en": (
            "✅ *Your bank transfer has been approved!*\n\n"
            "🔐 *Username:* `{username}`\n"
            "🔑 *Password:* `{password}`\n"
            "📅 Expires: {expires}"
        ),
    },
    "bank_rejected": {
        "fa": "❌ انتقال بانکی شما رد شد. برای پشتیبانی با ادمین تماس بگیرید.",
        "en": "❌ Your bank transfer was rejected. Please contact support.",
    },
    "topup_approved": {
        "fa": "✅ کیف پول شما شارژ شد!\nافزوده شد: *{amount}*\nموجودی جدید: *{balance}*",
        "en": "✅ Your wallet has been topped up!\nAdded: *{amount}*\nNew balance: *{balance}*",
    },
    "topup_rejected": {
        "fa": "❌ درخواست شارژ کیف پول رد شد. برای پشتیبانی با ادمین تماس بگیرید.",
        "en": "❌ Your wallet top-up was rejected. Please contact support.",
    },

    # ── Admin panel ──────────────────────────────────────────────────────────
    "admin_only": {"fa": "⛔ فقط ادمین.", "en": "⛔ Admins only."},
    "no_pending": {"fa": "پرداخت معلقی وجود ندارد.", "en": "No pending payments."},
    "already_processed": {"fa": "قبلاً پردازش شده.", "en": "Already processed."},
    "admin_ask_amount": {
        "fa": "مبلغ دریافتی (دلار) را وارد کنید:",
        "en": "Enter the amount received (USD):",
    },
    "admin_ask_receipt_number": {
        "fa": "شماره رسید / کد مرجع را وارد کنید:",
        "en": "Enter the receipt / reference number:",
    },
    "admin_receipt_already_used": {
        "fa": "❌ این شماره رسید قبلاً استفاده شده است. لطفاً شماره دیگری وارد کنید:",
        "en": "❌ This receipt number was already used. Enter a different one:",
    },
    "admin_invalid_amount": {
        "fa": "مبلغ نامعتبر. عدد مثبت وارد کنید:",
        "en": "Invalid amount. Enter a positive number:",
    },

    # ── Renewal ──────────────────────────────────────────────────────────────
    "renew_title": {
        "fa": "🔄 *تمدید اکانت*\n\nکدام اکانت را می‌خواهید تمدید کنید؟",
        "en": "🔄 *Renew Account*\n\nWhich account would you like to renew?",
    },
    "no_renewable": {
        "fa": "⚠️ هیچ اکانتی برای تمدید ندارید.\n\nابتدا یک پلن خریداری کنید.",
        "en": "⚠️ No accounts available for renewal.\n\nPurchase a plan first.",
    },
    "renew_select_plan": {
        "fa": "✅ اکانت انتخاب شد.\n\nپلن جدید را انتخاب کنید یا همان پلن فعلی را ادامه دهید:",
        "en": "✅ Account selected.\n\nChoose a plan or keep the current one:",
    },
    "btn_renew_back": {"fa": "🔙 بازگشت", "en": "🔙 Back"},

    # ── Account usage ─────────────────────────────────────────────────────────
    "usage_title": {
        "fa": "📊 *مشاهده مانده اکانت*\n\nکدام اکانت را می‌خواهید بررسی کنید؟",
        "en": "📊 *Account Usage*\n\nWhich account would you like to check?",
    },
    "no_active_accounts": {
        "fa": "⚠️ هیچ اکانت فعالی ندارید.",
        "en": "⚠️ No active accounts.",
    },
    "account_usage": {
        "fa": (
            "📊 *مانده اکانت*\n\n"
            "👤 نام کاربری: `{username}`\n"
            "📦 پلن: {plan}\n"
            "📅 انقضا: {expires}\n\n"
            "📶 *مصرف اینترنت:*\n"
            "⬇️ دریافت: {bytes_in}\n"
            "⬆️ ارسال: {bytes_out}\n"
            "📊 کل مصرف: {total_used}\n"
            "💾 مانده: {remaining}"
        ),
        "en": (
            "📊 *Account Usage*\n\n"
            "👤 Username: `{username}`\n"
            "📦 Plan: {plan}\n"
            "📅 Expires: {expires}\n\n"
            "📶 *Data Usage:*\n"
            "⬇️ Download: {bytes_in}\n"
            "⬆️ Upload: {bytes_out}\n"
            "📊 Total used: {total_used}\n"
            "💾 Remaining: {remaining}"
        ),
    },
    "usage_unavailable": {
        "fa": (
            "📊 *مانده اکانت*\n\n"
            "👤 نام کاربری: `{username}`\n"
            "📦 پلن: {plan}\n"
            "📅 انقضا: {expires}\n\n"
            "⚠️ اطلاعات مصرف در دسترس نیست."
        ),
        "en": (
            "📊 *Account Usage*\n\n"
            "👤 Username: `{username}`\n"
            "📦 Plan: {plan}\n"
            "📅 Expires: {expires}\n\n"
            "⚠️ Usage data is currently unavailable."
        ),
    },
}


def t(key: str, lang: str = "fa", **kwargs) -> str:
    """Return the translated string for key in the given language."""
    entry = TRANSLATIONS.get(key, {})
    text = entry.get(lang) or entry.get("fa") or f"[{key}]"
    return text.format(**kwargs) if kwargs else text


def get_user_lang(user) -> str:
    """Extract language from a User ORM object or a plain string."""
    if isinstance(user, str):
        return user
    return getattr(user, "language", "fa") or "fa"
