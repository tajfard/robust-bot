"""High-level VPN account lifecycle tied to orders."""
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from database.db import get_db
from database.models import Order, OrderStatus
from services import mikrotik


@dataclass
class ActivatedOrder:
    id: int
    vpn_username: str
    vpn_password: str
    expires_at: datetime


def _generate_username() -> str:
    digits = "".join(secrets.choice(string.digits) for _ in range(6))
    return f"vpn_{digits}"


def _username_is_free(username: str) -> bool:
    """Return True if this username is not already in the DB."""
    from database.db import get_db
    from database.models import Order
    with get_db() as db:
        return db.query(Order).filter(Order.vpn_username == username).first() is None


def _unique_username() -> str:
    for _ in range(20):
        u = _generate_username()
        if _username_is_free(u):
            return u
    raise RuntimeError("Could not generate a unique VPN username after 20 attempts")


def activate_order(order_id: int) -> ActivatedOrder:
    with get_db() as db:
        order = db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        if order.status == OrderStatus.ACTIVE:
            return ActivatedOrder(
                id=order.id,
                vpn_username=order.vpn_username,
                vpn_password=order.vpn_password,
                expires_at=order.expires_at,
            )

        tg_id = order.user.telegram_id
        duration = order.plan.duration_days
        mt_profile = order.plan.mikrotik_profile or ""

        # vpn_username pre-set → renewal: extend existing account
        if order.vpn_username:
            username = order.vpn_username
            password = order.vpn_password or ""
            mikrotik.enable_vpn_user(username)
            if mt_profile:
                mikrotik.update_user_profile(username, mt_profile)
            # Extend from current expiry or now, whichever is later
            prev = (
                db.query(Order)
                .filter(
                    Order.vpn_username == username,
                    Order.id != order.id,
                    Order.expires_at.isnot(None),
                )
                .order_by(Order.expires_at.desc())
                .first()
            )
            base = datetime.utcnow()
            if prev and prev.expires_at and prev.expires_at > base:
                base = prev.expires_at
            expires = base + timedelta(days=duration)
        else:
            username = _unique_username()
            comment = f"tg:{tg_id} order:{order.id}"
            if mikrotik.user_exists(username):
                mikrotik.enable_vpn_user(username)
                password = order.vpn_password or ""
            else:
                creds = mikrotik.create_vpn_user(username, comment, profile=mt_profile)
                password = creds["password"]
            expires = datetime.utcnow() + timedelta(days=duration)

        order.vpn_username = username
        order.vpn_password = password
        order.status = OrderStatus.ACTIVE
        order.activated_at = datetime.utcnow()
        order.expires_at = expires
        db.add(order)

        return ActivatedOrder(
            id=order.id,
            vpn_username=username,
            vpn_password=password,
            expires_at=expires,
        )


def expire_order(order_id: int):
    with get_db() as db:
        order = db.get(Order, order_id)
        if not order:
            return
        if order.vpn_username:
            mikrotik.disable_vpn_user(order.vpn_username)
        order.status = OrderStatus.EXPIRED
        db.add(order)


def check_and_expire_orders():
    """Called by scheduler — disable accounts that have passed their expiry date."""
    with get_db() as db:
        expired = (
            db.query(Order)
            .filter(
                Order.status == OrderStatus.ACTIVE,
                Order.expires_at <= datetime.utcnow(),
            )
            .all()
        )
        for order in expired:
            if order.vpn_username:
                mikrotik.disable_vpn_user(order.vpn_username)
            order.status = OrderStatus.EXPIRED
        db.commit()
