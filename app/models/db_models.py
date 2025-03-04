from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (DateTime, Enum, ForeignKey, Integer, Numeric, String,
                        UniqueConstraint)
from sqlalchemy.orm import (DeclarativeMeta, Mapped, declarative_base,
                            relationship)
from sqlalchemy.testing.schema import mapped_column

from ..schemas.enums import (CurrencyEnum, TransactionStatusEnum,
                             TransactionTypeEnum, UserRoleEnum, UserStatusEnum)

Base: DeclarativeMeta = declarative_base()


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped["UserRoleEnum"] = mapped_column(
        Enum(UserRoleEnum, native_enum=False, create_constraint=True), nullable=False, default=UserRoleEnum.USER
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped["UserStatusEnum"] = mapped_column(
        Enum(UserStatusEnum, native_enum=False, create_constraint=True), nullable=False, default=UserStatusEnum.ACTIVE
    )
    created: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now)

    user_balance: Mapped[list["UserBalance"]] = relationship("UserBalance", back_populates="owner")


class UserBalance(Base):
    __tablename__ = "user_balance"
    __table_args__ = (UniqueConstraint("user_id", "currency", name="user_balance_user_currency_unique"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    currency: Mapped["CurrencyEnum"] = mapped_column(
        Enum(CurrencyEnum, native_enum=False, create_constraint=True), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=6), nullable=False, default=0.0)
    created: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now)

    owner: Mapped["User"] = relationship("User", back_populates="user_balance")


class Transaction(Base):
    __tablename__ = "transaction"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    recipient_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    currency: Mapped["CurrencyEnum"] = mapped_column(
        Enum(CurrencyEnum, native_enum=False, create_constraint=True, name="currencyenum"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=6), nullable=False)
    type: Mapped["TransactionTypeEnum"] = mapped_column(
        Enum(TransactionTypeEnum, native_enum=False, create_constraint=True), nullable=False
    )
    from_currency: Mapped["CurrencyEnum"] = mapped_column(
        Enum(CurrencyEnum, native_enum=False, create_constraint=True, name="fromcurrencyenum"), nullable=True
    )
    to_currency: Mapped["CurrencyEnum"] = mapped_column(
        Enum(CurrencyEnum, native_enum=False, create_constraint=True, name="tocurrencyenum"), nullable=True
    )
    status: Mapped["TransactionStatusEnum"] = mapped_column(
        Enum(TransactionStatusEnum, native_enum=False, create_constraint=True), nullable=False
    )
    created: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now)
