import typing
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enums import (CurrencyEnum, TransactionStatusEnum,
                               TransactionTypeEnum)


class RequestTransactionModel(BaseModel):
    currency: CurrencyEnum
    amount: float
    type: TransactionTypeEnum
    recipient_id: typing.Optional[int] = None


class TransactionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: typing.Optional[int]
    sender_id: typing.Optional[int]
    recipient_id: typing.Optional[int] = None
    currency: typing.Optional[CurrencyEnum] = None
    amount: float
    type: typing.Optional[TransactionTypeEnum] = None
    status: typing.Optional[TransactionStatusEnum] = None
    created: typing.Optional[datetime] = None
