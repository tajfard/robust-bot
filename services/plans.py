"""Fixed plan catalog — seeded into DB on startup, never edited via bot UI."""
from config import (
    PLAN_PROFILE_TEST, PLAN_PROFILE_1GB, PLAN_PROFILE_5GB,
    PLAN_PROFILE_15GB, PLAN_PROFILE_50GB, USD_TO_TOOMAN,
)
from database.db import get_db
from database.models import Plan, Order, OrderStatus

# ── Catalog definition ────────────────────────────────────────────────────────
# bandwidth_gb: 0 = unlimited, 0.05 = 50 MB, etc.

_CATALOG = [
    dict(
        name="test",
        description="50 MB – 1 Day",
        duration_days=1,
        price_usd=0.0,
        bandwidth_gb=50/1024,   # exactly 50 MB
        simultaneous_connections=1,
        mikrotik_profile=PLAN_PROFILE_TEST,
        is_test=True,
    ),
    dict(
        name="1gb-1mo",
        description="1 GB – 1 Month",
        duration_days=30,
        price_usd=3.0,
        bandwidth_gb=1.0,
        simultaneous_connections=1,
        mikrotik_profile=PLAN_PROFILE_1GB,
        is_test=False,
    ),
    dict(
        name="5gb-1mo",
        description="5 GB – 1 Month",
        duration_days=30,
        price_usd=6.0,
        bandwidth_gb=5.0,
        simultaneous_connections=1,
        mikrotik_profile=PLAN_PROFILE_5GB,
        is_test=False,
    ),
    dict(
        name="15gb-1mo",
        description="15 GB – 1 Month",
        duration_days=30,
        price_usd=10.0,
        bandwidth_gb=15.0,
        simultaneous_connections=1,
        mikrotik_profile=PLAN_PROFILE_15GB,
        is_test=False,
    ),
    dict(
        name="50gb-3mo",
        description="50 GB – 3 Months",
        duration_days=90,
        price_usd=25.0,
        bandwidth_gb=50.0,
        simultaneous_connections=1,
        mikrotik_profile=PLAN_PROFILE_50GB,
        is_test=False,
    ),
]


def seed_plans():
    """Upsert the fixed catalog and remove any plans not in it (safe to call on every startup)."""
    catalog_names = {e["name"] for e in _CATALOG}
    with get_db() as db:
        # Remove obsolete plans that have no orders attached
        for plan in db.query(Plan).all():
            if plan.name not in catalog_names:
                if not plan.orders:
                    db.delete(plan)
                else:
                    plan.is_active = False  # keep for order history, just hide it

        # Upsert current catalog
        for entry in _CATALOG:
            plan = db.query(Plan).filter(Plan.name == entry["name"]).first()
            if plan:
                for k, v in entry.items():
                    setattr(plan, k, v)
            else:
                db.add(Plan(**entry))


# ── Display helpers ───────────────────────────────────────────────────────────

def _to_fa(n: int) -> str:
    """Integer → Persian digits with Persian thousands separator (٬)."""
    return f"{n:,}".translate(str.maketrans('0123456789,', '۰۱۲۳۴۵۶۷۸۹٬'))


def fmt_bandwidth(gb: float, lang: str) -> str:
    if gb == 0:
        return "نامحدود" if lang == "fa" else "Unlimited"
    if gb < 1:
        mb = int(round(gb * 1024))
        return f"{_to_fa(mb)} مگابایت" if lang == "fa" else f"{mb} MB"
    gb_int = int(gb)
    return f"{_to_fa(gb_int)} گیگابایت" if lang == "fa" else f"{gb_int} GB"


def fmt_duration(days: int, lang: str) -> str:
    if lang == "fa":
        if days == 1:   return "۱ روز"
        if days == 30:  return "۱ ماه"
        if days == 90:  return "۳ ماه"
        return f"{_to_fa(days)} روز"
    else:
        if days == 1:   return "1 Day"
        if days == 30:  return "1 Month"
        if days == 90:  return "3 Months"
        return f"{days} Days"


def fmt_price(price_usd: float, lang: str) -> str:
    if price_usd == 0:
        return "🆓 رایگان" if lang == "fa" else "🆓 Free"
    tooman = int(price_usd * USD_TO_TOOMAN)
    tooman_str = f"{tooman:,}"
    if lang == "fa":
        return f"${price_usd:.0f} ({tooman_str} تومان)"
    return f"${price_usd:.0f} ({tooman_str} Tomans)"


def fmt_usd(usd: float, lang: str) -> str:
    """Format a USD amount with Tooman equivalent: '$3.00 (1,800,000 تومان)'."""
    tooman = int(usd * USD_TO_TOOMAN)
    tooman_str = f"{tooman:,}"
    if lang == "fa":
        return f"${usd:.2f} ({tooman_str} تومان)"
    return f"${usd:.2f} ({tooman_str} Tomans)"


def fmt_plan_button(plan: Plan, lang: str) -> str:
    icon = "🆓" if plan.is_test else "📦"

    if lang == "fa":
        # All-Persian format: every character is RTL or neutral — no bidi mixing.
        # Arabic-Indic digits (۰–۹) + Persian words only; no Latin letters or $ sign.
        if plan.bandwidth_gb == 0:
            bw = "نامحدود"
        elif plan.bandwidth_gb < 1:
            bw = f"{_to_fa(int(round(plan.bandwidth_gb * 1024)))} مگ"
        else:
            bw = f"{_to_fa(int(plan.bandwidth_gb))} گیگ"

        if plan.duration_days == 1:    dur = "۱ روز"
        elif plan.duration_days == 30: dur = "۱ ماه"
        elif plan.duration_days == 90: dur = "۳ ماه"
        else:                          dur = f"{_to_fa(plan.duration_days)} روز"

        if plan.price_usd == 0:
            price = "رایگان"
        else:
            tooman_fa = _to_fa(int(plan.price_usd * USD_TO_TOOMAN))
            usd_fa = _to_fa(int(plan.price_usd))
            # Use Persian comma ، to avoid mirrored Latin parentheses in RTL rendering
            price = f"{usd_fa} دلار، {tooman_fa} تومان"

        # ‏ (RIGHT-TO-LEFT MARK, bidi class R) forces RTL paragraph direction.
        # Icon is placed at the end so 🆓 (bidi L) doesn't affect direction detection.
        return f"‏{bw} | {dur} | {price} {icon}"
    else:
        bw = fmt_bandwidth(plan.bandwidth_gb, lang)
        dur = fmt_duration(plan.duration_days, lang)
        price = fmt_price(plan.price_usd, lang)
        return f"{icon} {bw} | {dur} | {price}"


# ── Test plan eligibility ─────────────────────────────────────────────────────

def has_used_test_plan(user_id: int, plan_id: int) -> bool:
    """Return True only if the user has a successfully activated or expired test account.
    PENDING/PAID orders without credentials (failed activations) are ignored."""
    with get_db() as db:
        return db.query(Order).filter(
            Order.user_id == user_id,
            Order.plan_id == plan_id,
            Order.status.in_([OrderStatus.ACTIVE, OrderStatus.EXPIRED]),
        ).first() is not None
