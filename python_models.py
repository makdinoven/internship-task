import typing
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel
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
    processed = "PROCESSED"
    roll_backed = "ROLLBACKED"



class RequestUserModel(BaseModel):
    email: str

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
        if "amount" in values and values.get("amount"):
            if values["amount"] < 0:
                raise ValueError("Amount cannot be negative")

        return values

class RequestTransactionModel(BaseModel):
    currency: CurrencyEnum
    amount: float

class TransactionModel(BaseModel):
    id: typing.Optional[int]
    user_id: typing.Optional[int] = None
    currency: typing.Optional[CurrencyEnum] = None
    amount: typing.Optional[float] = None
    status: typing.Optional[TransactionStatusEnum] = None
    created: typing.Optional[datetime] = None
