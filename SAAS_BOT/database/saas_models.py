from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Float
from sqlalchemy.orm import DeclarativeBase


class SaasBase(DeclarativeBase):
    pass


class SaasClient(SaasBase):
    """A client who bought a bot subscription."""
    __tablename__ = "saas_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)

    # Client's bot configuration
    bot_token = Column(String, nullable=True)
    bot_username = Column(String, nullable=True)       # filled after validation

    # Client's Kaspi details (for their own customers)
    kaspi_phone = Column(String, nullable=True)
    kaspi_receiver = Column(String, nullable=True)

    # Subscription
    is_active = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Registration state machine
    state = Column(String, default="start")
    # states: start → awaiting_token → awaiting_kaspi_phone →
    #         awaiting_kaspi_receiver → awaiting_payment → active


class SaasPayment(SaasBase):
    """Payment for a bot subscription."""
    __tablename__ = "saas_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_tg_id = Column(BigInteger, nullable=False)
    amount = Column(Float, default=5000.0)
    receipt_file_id = Column(String, nullable=True)
    status = Column(String, default="pending")   # pending / approved / rejected
    created_at = Column(DateTime, default=datetime.utcnow)
