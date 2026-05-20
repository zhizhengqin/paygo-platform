"""SQLAlchemy ORM 模型 — 5 张表：customers, tokens, sms_records, payment_rates, device_states。"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import (
    Column, String, Integer, Numeric, Text, Date, DateTime, ForeignKey, JSON, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _new_id(prefix: str) -> str:
    return f"{prefix}{str(uuid.uuid4())[:4].upper()}"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("C"))
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    device_id = Column(String(50), nullable=False, unique=True)
    secret_key = Column(String(64), nullable=True)  # 改为可空，迁移后废弃
    secret_key_encrypted = Column(Text, nullable=True)  # Fernet 加密密文
    count = Column(Integer, default=0)
    status = Column(String(20), default="locked")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
    locked_at = Column(DateTime(timezone=True), nullable=True)
    address = Column(Text, nullable=True)
    gps_latitude = Column(Numeric(10, 8), nullable=True)
    gps_longitude = Column(Numeric(11, 8), nullable=True)
    id_number = Column(String(50), nullable=True)
    mfi_id = Column(String(8), ForeignKey("mfis.id"), nullable=True, index=True)
    tags = Column(JSON, nullable=True, default=list)

    tokens = relationship("Token", back_populates="customer", lazy="selectin",
                          cascade="all, delete-orphan")
    sms_records = relationship("SmsRecord", back_populates="customer", lazy="selectin",
                               cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="customer", lazy="selectin",
                             cascade="all, delete-orphan")


class Mfi(Base):
    """MFI 小额信贷机构"""
    __tablename__ = "mfis"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("MF"))
    name = Column(String(100), nullable=False)
    branch = Column(String(100), nullable=True)
    contact_info = Column(Text, nullable=True)
    api_endpoint = Column(String(255), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())


class Token(Base):
    __tablename__ = "tokens"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("T"))
    customer_id = Column(String(8), ForeignKey("customers.id"), nullable=False, index=True)
    token = Column(String(9), nullable=False)
    days = Column(Integer, nullable=False)
    amount = Column(Numeric(10, 2), default=0)
    contract_id = Column(String(8), ForeignKey("contracts.id"), nullable=True, index=True)
    status = Column(String(20), default="UNUSED")  # UNUSED / USED / SUPERSEDED
    superseded_by = Column(String(8), nullable=True)  # 替换 Token ID
    voided_at = Column(DateTime(timezone=True), nullable=True)
    voided_by = Column(String(100), nullable=True)
    void_reason = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    count = Column(Integer, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
    expires_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now() + timedelta(days=7))

    customer = relationship("Customer", back_populates="tokens")

    __table_args__ = (
        Index("ix_tokens_expires_at", "expires_at"),
    )


class SmsRecord(Base):
    __tablename__ = "sms_records"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("S"))
    customer_id = Column(String(8), ForeignKey("customers.id"), nullable=False)
    to_phone = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now())

    customer = relationship("Customer", back_populates="sms_records")


class PaymentRate(Base):
    __tablename__ = "payment_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Numeric(10, 2), nullable=False, unique=True)
    days = Column(Integer, nullable=False)


class DeviceState(Base):
    __tablename__ = "device_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), nullable=False, unique=True, index=True)
    secret_key = Column(String(64), nullable=True)
    count = Column(Integer, default=0)
    used_counts = Column(JSON, default=list)
    remaining_days = Column(Integer, default=0)
    last_update = Column(Date, nullable=True)
    status = Column(String(20), default="unbound")


class LoanProduct(Base):
    """贷款产品配置表"""
    __tablename__ = "loan_products"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("LP"))
    name = Column(String(100), nullable=False)
    capacity_kw = Column(Numeric(5, 2), nullable=False)
    term_months = Column(Integer, nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False)
    down_payment_pct = Column(Numeric(5, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())


class Contract(Base):
    """合同表"""
    __tablename__ = "contracts"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("CT"))
    contract_no = Column(String(30), nullable=False, unique=True)
    customer_id = Column(String(8), ForeignKey("customers.id"), nullable=False, index=True)
    product_id = Column(String(8), ForeignKey("loan_products.id"), nullable=False)
    down_payment = Column(Numeric(12, 2), nullable=False)
    loan_amount = Column(Numeric(12, 2), nullable=False)
    monthly_payment = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="draft")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    remaining_days = Column(Integer, default=0)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())

    customer = relationship("Customer", back_populates="contracts", lazy="selectin")
    schedules = relationship("RepaymentSchedule", back_populates="contract",
                             lazy="selectin", cascade="all, delete-orphan")


class RepaymentSchedule(Base):
    """还款计划表"""
    __tablename__ = "repayment_schedules"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("RS"))
    contract_id = Column(String(8), ForeignKey("contracts.id"), nullable=False, index=True)
    period_no = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    principal = Column(Numeric(10, 2), nullable=False)
    interest = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default="pending")

    contract = relationship("Contract", back_populates="schedules")


class RepaymentRecord(Base):
    """实际还款记录 — 关联还款计划与 Token"""
    __tablename__ = "repayment_records"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("RR"))
    contract_id = Column(String(8), ForeignKey("contracts.id"), nullable=False, index=True)
    schedule_id = Column(String(8), ForeignKey("repayment_schedules.id"), nullable=False)
    token_id = Column(String(8), ForeignKey("tokens.id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(20), default="Bakong")
    paid_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
