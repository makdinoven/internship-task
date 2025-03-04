from enum import StrEnum


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


class TransactionTypeEnum(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    EXCHANGE = "EXCHANGE"


class UserRoleEnum(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class TransactionDirectionEnum(StrEnum):
    RECEIVED = "RECEIVED"
    SENT = "SENT"
