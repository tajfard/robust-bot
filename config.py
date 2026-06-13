import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

MIKROTIK_HOST = os.getenv("MIKROTIK_HOST", "192.168.1.1")
MIKROTIK_PORT = int(os.getenv("MIKROTIK_PORT", "8728"))
MIKROTIK_USER = os.getenv("MIKROTIK_USER", "admin")
MIKROTIK_PASSWORD = os.getenv("MIKROTIK_PASSWORD", "")
# Per-plan User Manager profile names
PLAN_PROFILE_TEST  = os.getenv("PLAN_PROFILE_TEST",  "test")
PLAN_PROFILE_1GB   = os.getenv("PLAN_PROFILE_1GB",   "1gb-1mo")
PLAN_PROFILE_5GB   = os.getenv("PLAN_PROFILE_5GB",   "5gb-1mo")
PLAN_PROFILE_15GB  = os.getenv("PLAN_PROFILE_15GB",  "15gb-1mo")
PLAN_PROFILE_50GB  = os.getenv("PLAN_PROFILE_50GB",  "50gb-3mo")

# Currency
USD_TO_TOOMAN = int(os.getenv("USD_TO_TOOMAN", "600000"))

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

TRON_WALLET_ADDRESS = os.getenv("TRON_WALLET_ADDRESS", "")
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "")

ETH_WALLET_ADDRESS = os.getenv("ETH_WALLET_ADDRESS", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

BANK_CARD_NUMBER = os.getenv("BANK_CARD_NUMBER", "")
BANK_ACCOUNT_NAME = os.getenv("BANK_ACCOUNT_NAME", "")
BANK_NAME = os.getenv("BANK_NAME", "")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vpn_bot.db")

# Payment check interval in seconds (scheduler)
CRYPTO_CHECK_INTERVAL = 60

# Webhook
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN", "bot.robustvpn.host")
WEBHOOK_PORT   = int(os.getenv("WEBHOOK_PORT", "8443"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")   # random string, set in .env

# Path to the OpenVPN config file sent to users after order activation
VPN_CONFIG_FILE = os.getenv("VPN_CONFIG_FILE", "client_rorbustvpn_iran.ovpn")
