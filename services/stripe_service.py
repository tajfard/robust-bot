import stripe
from config import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY


def create_payment_link(amount_usd: float, order_id: int, description: str) -> tuple[str, str]:
    """Create a Stripe Checkout Session and return (session_id, checkout_url)."""
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": int(amount_usd * 100),
                "product_data": {"name": description},
            },
            "quantity": 1,
        }],
        mode="payment",
        metadata={"order_id": str(order_id)},
        success_url="https://t.me/robustvpn_bot",
        cancel_url="https://t.me/robustvpn_bot",
    )
    return session.id, session.url


def retrieve_session(session_id: str) -> stripe.checkout.Session:
    return stripe.checkout.Session.retrieve(session_id)
