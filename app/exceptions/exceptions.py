from typing import Optional

from fastapi import HTTPException, status
from starlette.status import (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN,
                              HTTP_404_NOT_FOUND,
                              HTTP_422_UNPROCESSABLE_ENTITY)


class UserAlreadyExistsException(HTTPException):
    def __init__(self, email: Optional[str] = None) -> None:
        if email is not None:
            detail = f"User {email} already exists."
        else:
            detail = "User already exist."
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class UserNotExistsException(HTTPException):
    def __init__(self, user_id: Optional[int] = None) -> None:
        if user_id is not None:
            detail = f"User with id {user_id} not found."
        else:
            detail = "User not found."
        super().__init__(detail=detail, status_code=HTTP_404_NOT_FOUND)


class UserAlreadyBlockedException(HTTPException):
    def __init__(self, user_id: Optional[int] = None) -> None:
        if user_id is not None:
            detail = f"User with id {user_id} is already blocked."
        else:
            detail = "User is already blocked."
        super().__init__(detail=detail, status_code=HTTP_400_BAD_REQUEST)


class UserAlreadyActiveException(HTTPException):
    def __init__(self, user_id: Optional[int] = None) -> None:
        if user_id is not None:
            detail = f"User with id {user_id} is already active."
        else:
            detail = "User is already active."
        super().__init__(detail=detail, status_code=HTTP_400_BAD_REQUEST)


class BadRequestDataException(HTTPException):
    def __init__(self, detail: str = "Bad request data") -> None:
        super().__init__(detail=detail, status_code=HTTP_422_UNPROCESSABLE_ENTITY)


class NegativeBalanceException(HTTPException):
    def __init__(self, balance: Optional[float] = None) -> None:
        if balance is not None:
            detail = f"Negative balance : {balance}."
        else:
            detail = "Negative balance"
        super().__init__(detail=detail, status_code=HTTP_400_BAD_REQUEST)


class TransactionNotExistsException(HTTPException):
    def __init__(self, transaction_id: Optional[int] = None) -> None:
        if transaction_id is not None:
            detail = f"Transaction with id {transaction_id} not found."
        else:
            detail = "Transaction not found."
        super().__init__(detail=detail, status_code=HTTP_404_NOT_FOUND)


class TransactionDoesNotBelongToUserException(HTTPException):
    def __init__(self, transaction_id: Optional[int] = None) -> None:
        if transaction_id is not None:
            detail = f"Transaction with id {transaction_id} belongs to user not found."
        else:
            detail = "Transaction does not belong to user."
        super().__init__(detail=detail, status_code=HTTP_403_FORBIDDEN)


class CreateTransactionForBlockedUserException(HTTPException):
    def __init__(self, user_id: Optional[int] = None) -> None:
        if user_id is not None:
            detail = f"Cannot create transaction with id {user_id} because the user is already blocked."
        else:
            detail = "Cannot create transaction for blocked user."
        super().__init__(detail=detail, status_code=HTTP_403_FORBIDDEN)


class UpdateTransactionForBlockedUserException(HTTPException):
    def __init__(self, user_id: Optional[int] = None) -> None:
        if user_id is not None:
            detail = f"Cannot update transaction with id {user_id} because the user is already blocked."
        else:
            detail = "Cannot update transaction for blocked user."
        super().__init__(detail=detail, status_code=HTTP_403_FORBIDDEN)


class TransactionAlreadyRollbackedException(HTTPException):
    def __init__(self, transaction_id: Optional[int] = None) -> None:
        if transaction_id is not None:
            detail = f"Transaction with id {transaction_id} already rolled backed."
        else:
            detail = "Transaction already rolled backed."
        super().__init__(detail=detail, status_code=HTTP_400_BAD_REQUEST)


class InvalidCredentialsException(HTTPException):
    def __init__(self) -> None:
        detail = "Invalid credentials."
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(HTTPException):
    def __init__(self) -> None:
        detail = "Token's lifetime has expired"
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenException(HTTPException):
    def __init__(self) -> None:
        detail = "Invalid token"
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InsufficientPrivilegesException(HTTPException):
    def __init__(self) -> None:
        detail = "Insufficient access rights"
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class ExchangeConversionException(HTTPException):
    def __init__(self, detail: Optional[str] = "Currency conversion failed") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class CurrencyRateFetchException(HTTPException):
    def __init__(self, detail: Optional[str] = "Failed to fetch currency rates") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UnsupportedCurrencyPairException(HTTPException):
    def __init__(self, from_currency: Optional[str] = None, to_currency: Optional[str] = None) -> None:
        if from_currency and to_currency:
            detail = f"Unsupported currency pair: {from_currency} -> {to_currency}"
        else:
            detail = "Unsupported currency pair"
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)
