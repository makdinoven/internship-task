import typing
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr
from pydantic.v1 import root_validator


class CurrencyEnum(StrEnum):
    USD = "USD"
    EUR = "EUR"
    AUD = "AUD"
    CAD = "CAD"
    ARS = "ARS"
    PLN = "PLN"
    BTC = "BTC"
    ETH = "ETH"
    DOGE = "DOGE"
    USDT = "USDT"


class UserStatusEnum(StrEnum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class TransactionStatusEnum(StrEnum):
    PROCESSED = "PROCESSED"
    ROLLBACKED = "ROLLBACKED"
    SUCCESS = "SUCCESS"

class TransactionTypeEnum(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class RequestUserModel(BaseModel):
    email: EmailStr

class RequestUserUpdateModel(BaseModel):
    status: UserStatusEnum


class ResponseUserBalanceModel(BaseModel):
    currency: typing.Optional[CurrencyEnum] = None
    amount: typing.Optional[float] = None


class ResponseUserModel(BaseModel):
    id: typing.Optional[int]
    email: typing.Optional[str] = None
    status: typing.Optional[UserStatusEnum] = None
    created: typing.Optional[datetime] = None
    balances: typing.Optional[typing.List[ResponseUserBalanceModel]] = None


class UserModel(BaseModel):
    id: typing.Optional[int]
    email: typing.Optional[str] = None
    status: typing.Optional[UserStatusEnum] = None
    created: typing.Optional[datetime] = None


class UserBalanceModel(BaseModel):
    id: typing.Optional[int]
    user_id: typing.Optional[int] = None
    currency: typing.Optional[CurrencyEnum] = None
    amount: typing.Optional[float] = None

    @root_validator(pre=True)
    def validate_not_negative(self, values):
        if "amount" in values and values.get("amount") is not None :
            if values["amount"] < 0:
                raise ValueError("Amount cannot be negative")
        return values


class RequestTransactionModel(BaseModel):
    currency: CurrencyEnum
    amount: float
    type: TransactionTypeEnum


class TransactionModel(BaseModel):
    id: typing.Optional[int]
    user_id: typing.Optional[int] = None
    currency: typing.Optional[CurrencyEnum] = None
    amount: typing.Optional[float] = None
    type: typing.Optional[TransactionTypeEnum] = None
    status: typing.Optional[TransactionStatusEnum] = None
    created: typing.Optional[datetime] = None
