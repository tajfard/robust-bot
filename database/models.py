from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class PaymentMethod(str, enum.Enum):
    STRIPE = "stripe"
    USDT_TRC20 = "usdt_trc20"
    USDT_ERC20 = "usdt_erc20"
    WALLET = "wallet"
    BANK_TRANSFER = "bank_transfer"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(64))
    full_name = Column(String(128))
    wallet_balance = Column(Float, default=0.0)
    language = Column(String(4), default="fa")  # 'fa' or 'en'
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    description = Column(Text)
    duration_days = Column(Integer, nullable=False)
    price_usd = Column(Float, nullable=False)
    bandwidth_gb = Column(Float, default=0.0)   # 0 = unlimited; <1 means MB-range (e.g. 0.05 = 50 MB)
    simultaneous_connections = Column(Integer, default=1)
    mikrotik_profile = Column(String(64))       # User Manager profile name for this plan
    is_test = Column(Boolean, default=False)    # free once-only test account
    is_active = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="plan")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_method = Column(Enum(PaymentMethod))
    amount_paid = Column(Float, default=0.0)
    vpn_username = Column(String(64))
    vpn_password = Column(String(64))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)

    user = relationship("User", back_populates="orders")
    plan = relationship("Plan", back_populates="orders")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_usd = Column(Float, nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    tx_hash = Column(String(128))           # crypto tx hash or Stripe payment intent
    receipt_number = Column(String(128))    # admin-entered bank receipt/ref number (unique per confirmed tx)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    admin_note = Column(Text)
    receipt_file_id = Column(String(256))   # Telegram file_id for bank transfer receipt photo
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)

    user = relationship("User", back_populates="transactions")
