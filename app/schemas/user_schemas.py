import typing
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, root_validator

from .enums import CurrencyEnum, UserRoleEnum, UserStatusEnum


class RequestUserModel(BaseModel):
    email: EmailStr
    password: str


class RequestUserUpdateModel(BaseModel):
    status: UserStatusEnum


class ResponseUserBalanceModel(BaseModel):
    currency: typing.Optional[CurrencyEnum] = None
    amount: float


class ResponseUserModel(BaseModel):
    id: typing.Optional[int]
    email: typing.Optional[str] = None
    role: typing.Optional[UserRoleEnum] = None
    status: typing.Optional[UserStatusEnum] = None
    created: typing.Optional[datetime] = None
    balances: typing.Optional[typing.List[ResponseUserBalanceModel]] = None


class UserModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: typing.Optional[int]
    email: typing.Optional[str] = None
    status: typing.Optional[UserStatusEnum] = None
    created: typing.Optional[datetime] = None


class UserBalanceModel(BaseModel):
    id: typing.Optional[int]
    user_id: typing.Optional[int] = None
    currency: typing.Optional[CurrencyEnum] = None
    amount: float

    @root_validator(pre=True)
    def validate_not_negative(self, values):
        if "amount" in values and values.get("amount") is not None:
            if values["amount"] < 0:
                raise ValueError("Amount cannot be negative")
        return values
