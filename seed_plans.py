"""Run once to seed sample VPN plans into the database."""
from database.db import init_db, get_db
from database.models import Plan

PLANS = [
    dict(name="Basic", description="1 month VPN access", duration_days=30,
         price_usd=5.00, bandwidth_gb=50, simultaneous_connections=1),
    dict(name="Standard", description="1 month unlimited bandwidth", duration_days=30,
         price_usd=9.99, bandwidth_gb=0, simultaneous_connections=2),
    dict(name="Pro 3 months", description="3 months unlimited", duration_days=90,
         price_usd=24.99, bandwidth_gb=0, simultaneous_connections=3),
]

if __name__ == "__main__":
    init_db()
    with get_db() as db:
        for p in PLANS:
            db.add(Plan(**p))
    print("Plans seeded successfully.")
