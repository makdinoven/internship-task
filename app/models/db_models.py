from datetime import datetime

from sqlalchemy import (Column, DateTime, Enum, ForeignKey, Integer, Numeric,
                        String, UniqueConstraint)
from sqlalchemy.orm import DeclarativeMeta, declarative_base, relationship

from ..schemas.enums import (CurrencyEnum, TransactionStatusEnum,
                             TransactionTypeEnum, UserRoleEnum, UserStatusEnum)

Base: DeclarativeMeta = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    role = Column(
        Enum(UserRoleEnum, native_enum=False, create_constraint=True), nullable=False, default=UserRoleEnum.USER
    )
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    status = Column(
        Enum(UserStatusEnum, native_enum=False, create_constraint=True), nullable=False, default=UserStatusEnum.ACTIVE
    )
    created = Column(DateTime(timezone=True), nullable=True, default=datetime.now)

    user_balance = relationship("UserBalance", back_populates="owner")


class UserBalance(Base):
    __tablename__ = "user_balance"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    currency = Column(Enum(CurrencyEnum, native_enum=False, create_constraint=True), nullable=False)
    amount = Column(Numeric(precision=12, scale=6), nullable=False, default=0.0)
    created = Column(DateTime(timezone=True), nullable=True, default=datetime.now)
    UniqueConstraint("user_id", "currency", name="user_balance_user_currency_unique")

    owner = relationship("User", back_populates="user_balance")


class Transaction(Base):
    __tablename__ = "transaction"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    currency = Column(Enum(CurrencyEnum, native_enum=False, create_constraint=True), nullable=False)
    amount = Column(Numeric(precision=12, scale=6), nullable=False)
    type = Column(Enum(TransactionTypeEnum, native_enum=False, create_constraint=True), nullable=False)
    status = Column(Enum(TransactionStatusEnum, native_enum=False, create_constraint=True), nullable=False)
    created = Column(DateTime(timezone=True), nullable=True, default=datetime.now)
