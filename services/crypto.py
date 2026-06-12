"""Check USDT TRC20 and ERC20 payments against wallet addresses."""
import requests
from config import (
    TRON_WALLET_ADDRESS, TRONGRID_API_KEY,
    ETH_WALLET_ADDRESS, ETHERSCAN_API_KEY,
)

USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_ERC20_CONTRACT = "0xdac17f958d2ee523a2206206994597c13d831ec7"


def check_trc20_payment(
    since_timestamp_ms: int,
    min_amount_usdt: float = 0.0,
) -> tuple[str, float] | None:
    """Return (tx_hash, actual_usdt_amount) for the first inbound TRC20 USDT tx
    that is >= min_amount_usdt and arrived after since_timestamp_ms, else None."""
    url = f"https://api.trongrid.io/v1/accounts/{TRON_WALLET_ADDRESS}/transactions/trc20"
    headers = {"TRON-PRO-API-KEY": TRONGRID_API_KEY}
    params = {
        "limit": 50,
        "contract_address": USDT_TRC20_CONTRACT,
        "only_to": "true",
        "min_timestamp": since_timestamp_ms,
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception:
        return None

    threshold = int(min_amount_usdt * 1_000_000)
    for tx in data:
        value = int(tx.get("value", 0))
        if value >= threshold:
            actual_usdt = value / 1_000_000
            return tx.get("transaction_id"), actual_usdt
    return None


def check_erc20_payment(
    since_timestamp: int,
    min_amount_usdt: float = 0.0,
) -> tuple[str, float] | None:
    """Return (tx_hash, actual_usdt_amount) for the first inbound ERC20 USDT tx
    that is >= min_amount_usdt and arrived after since_timestamp, else None."""
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": USDT_ERC20_CONTRACT,
        "address": ETH_WALLET_ADDRESS,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("result", [])
    except Exception:
        return None

    threshold = int(min_amount_usdt * 1_000_000)
    for tx in result:
        if int(tx.get("timeStamp", 0)) < since_timestamp:
            break
        if tx.get("to", "").lower() == ETH_WALLET_ADDRESS.lower():
            value = int(tx.get("value", 0))
            if value >= threshold:
                actual_usdt = value / 1_000_000
                return tx.get("hash"), actual_usdt
    return None


def verify_trc20_tx(tx_hash: str, min_amount_usdt: float, since_ms: int) -> tuple[str, float] | None:
    """Verify a specific TRC20 USDT transaction by hash. Returns (tx_hash, amount) or None."""
    url = f"https://api.trongrid.io/v1/accounts/{TRON_WALLET_ADDRESS}/transactions/trc20"
    headers = {"TRON-PRO-API-KEY": TRONGRID_API_KEY}
    params = {
        "limit": 200,
        "contract_address": USDT_TRC20_CONTRACT,
        "only_to": "true",
        "min_timestamp": since_ms,
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception:
        return None

    threshold = int(min_amount_usdt * 1_000_000)
    for tx in data:
        if tx.get("transaction_id") == tx_hash:
            if tx.get("to", "").lower() != TRON_WALLET_ADDRESS.lower():
                return None  # transaction goes to a different address
            value = int(tx.get("value", 0))
            if value >= threshold:
                return tx_hash, value / 1_000_000
            return None  # found but insufficient
    return None


def verify_erc20_tx(tx_hash: str, min_amount_usdt: float, since_ts: int) -> tuple[str, float] | None:
    """Verify a specific ERC20 USDT transaction by hash. Returns (tx_hash, amount) or None."""
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": USDT_ERC20_CONTRACT,
        "address": ETH_WALLET_ADDRESS,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("result", [])
    except Exception:
        return None

    threshold = int(min_amount_usdt * 1_000_000)
    for tx in result:
        if int(tx.get("timeStamp", 0)) < since_ts:
            break
        if tx.get("hash", "").lower() == tx_hash.lower():
            if tx.get("to", "").lower() == ETH_WALLET_ADDRESS.lower():
                value = int(tx.get("value", 0))
                if value >= threshold:
                    return tx_hash, value / 1_000_000
            return None  # found but wrong recipient or amount
    return None


def is_tx_hash_used(tx_hash: str) -> bool:
    """Return True if this tx hash is already recorded in the transactions table."""
    from database.db import get_db
    from database.models import Transaction
    with get_db() as db:
        return db.query(Transaction).filter(Transaction.tx_hash == tx_hash).first() is not None
