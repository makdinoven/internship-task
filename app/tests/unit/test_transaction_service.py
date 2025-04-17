from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.exceptions.exceptions import (
    CreateTransactionForBlockedUserException, NegativeBalanceException,
    TransactionAlreadyRollbackedException, TransactionNotExistsException,
    UpdateTransactionForBlockedUserException)
from app.models.db_models import Transaction, UserBalance
from app.schemas.enums import (CurrencyEnum, TransactionDirectionEnum,
                               TransactionStatusEnum, TransactionTypeEnum,
                               UserStatusEnum)
from app.schemas.transaction_schemas import RequestTransactionModel
from app.schemas.user_schemas import RequestUserModel
from app.services import transaction_service, user_service
from app.tests.utils_test import uniq_email


@pytest.fixture
def usd_balance(db_session):
    async def _maker(user_id: int, amount: int | float = 0):
        query = (
            select(UserBalance)
            .where(
                UserBalance.user_id == user_id,
                UserBalance.currency == CurrencyEnum.USD.value,
            )
            .limit(1)
        )
        existing = (await db_session.execute(query)).scalars().first()

        if existing:
            existing.amount = Decimal(amount)
            balance = existing
        else:
            balance = UserBalance(
                user_id=user_id,
                currency=CurrencyEnum.USD.value,
                amount=Decimal(amount),
            )
            db_session.add(balance)

        await db_session.flush()
        return balance

    return _maker


@pytest.mark.asyncio
async def test_create_deposit(db_session, usd_balance):
    """Создание депозита корректно обновляет баланс."""
    user = await user_service.create_user(RequestUserModel(email=uniq_email("dep"), password="pass"), db_session)
    await usd_balance(user.id, 0)

    tx = await transaction_service.create_transaction(
        db_session,
        user.id,
        RequestTransactionModel(
            amount=Decimal(100),
            currency=CurrencyEnum.USD,
            type=TransactionTypeEnum.DEPOSIT,
        ),
    )

    assert isinstance(tx, Transaction)
    assert tx.amount == Decimal("100")

    bal = (
        await db_session.execute(
            select(UserBalance).where(
                UserBalance.user_id == user.id,
                UserBalance.currency == CurrencyEnum.USD.value,
            )
        )
    ).scalar_one()
    assert bal.amount == Decimal("100")


@pytest.mark.asyncio
async def test_get_transactions_filters(db_session, usd_balance):
    """Фильтры возвращают именно нужные транзакции."""
    user = await user_service.create_user(RequestUserModel(email=uniq_email("filters"), password="pass"), db_session)
    await usd_balance(user.id, 300)

    # withdrawal
    await transaction_service.create_transaction(
        db_session,
        user.id,
        RequestTransactionModel(amount=50, currency=CurrencyEnum.USD.value, type=TransactionTypeEnum.WITHDRAWAL),
    )
    # deposit
    await transaction_service.create_transaction(
        db_session,
        user.id,
        RequestTransactionModel(amount=70, currency=CurrencyEnum.USD, type=TransactionTypeEnum.DEPOSIT),
    )

    sent = await transaction_service.get_transactions(user.id, db_session, TransactionDirectionEnum.SENT)
    received = await transaction_service.get_transactions(user.id, db_session, TransactionDirectionEnum.RECEIVED)

    assert (tx.type in [TransactionTypeEnum.WITHDRAWAL, TransactionTypeEnum.TRANSFER] for tx in sent)
    assert (tx.type == TransactionTypeEnum.DEPOSIT for tx in received)


@pytest.mark.asyncio
async def test_withdraw_insufficient_funds(db_session, usd_balance):
    """Недостаточно средств при выводе - NegativeBalanceException."""
    user = await user_service.create_user(RequestUserModel(email=uniq_email("no_funds"), password="pass"), db_session)
    await usd_balance(user.id, 20)  # balance < amount

    with pytest.raises(NegativeBalanceException):
        await transaction_service.create_transaction(
            db_session,
            user.id,
            RequestTransactionModel(
                amount=100,
                currency=CurrencyEnum.USD,
                type=TransactionTypeEnum.WITHDRAWAL,
            ),
        )


@pytest.mark.asyncio
async def test_transfer_to_blocked_user(db_session, usd_balance):
    sender = await user_service.create_user(RequestUserModel(email=uniq_email("snd"), password="p"), db_session)
    await usd_balance(sender.id, 200)

    recipient = await user_service.create_user(RequestUserModel(email=uniq_email("blck"), password="p"), db_session)
    recipient.status = UserStatusEnum.BLOCKED
    db_session.add(recipient)
    await db_session.commit()

    with pytest.raises(CreateTransactionForBlockedUserException):
        await transaction_service.create_transaction(
            db_session,
            sender.id,
            RequestTransactionModel(
                amount=50,
                currency=CurrencyEnum.USD,
                type=TransactionTypeEnum.TRANSFER,
                recipient_id=recipient.id,
            ),
        )


@pytest.mark.asyncio
async def test_invalid_type(db_session, usd_balance):
    """Неверный тип транзакции - BadRequestDataException."""
    user = await user_service.create_user(RequestUserModel(email=uniq_email("badtype"), password="pass"), db_session)
    await usd_balance(user.id, 0)

    # подсовываем «несуществующий» тип через прямой cast к Enum
    class _FakeEnum(str):  # type: ignore
        value = "unknown"

    with pytest.raises(ValidationError):
        RequestTransactionModel(
            amount=1,
            currency=CurrencyEnum.USD,
            type=_FakeEnum(),  # type: ignore
        )


@pytest.mark.asyncio
async def test_rollback_deposit(db_session, usd_balance):
    user = await user_service.create_user(RequestUserModel(email=uniq_email("rb_dep"), password="x"), db_session)
    bal = await usd_balance(user.id, 0)

    tx = await transaction_service.create_transaction(
        db_session,
        user.id,
        RequestTransactionModel(amount=100, currency=CurrencyEnum.USD, type=TransactionTypeEnum.DEPOSIT),
    )

    assert bal.amount == Decimal("100")

    # делаем откат
    rolled = await transaction_service.patch_rollback_transaction(tx.id, db_session)

    bal_after = (await db_session.execute(select(UserBalance).where(UserBalance.id == bal.id))).scalar_one()
    assert bal_after.amount == Decimal("0")
    assert rolled.status == TransactionStatusEnum.ROLLBACKED


@pytest.mark.asyncio
async def test_rollback_withdrawal(db_session, usd_balance):
    """Откат вывода возвращает деньги на баланс."""
    user = await user_service.create_user(RequestUserModel(email=uniq_email("rb_wd"), password="x"), db_session)
    bal = await usd_balance(user.id, 200)

    tx = await transaction_service.create_transaction(
        db_session,
        user.id,
        RequestTransactionModel(amount=150, currency=CurrencyEnum.USD, type=TransactionTypeEnum.WITHDRAWAL),
    )
    assert bal.amount == Decimal("50")

    rolled = await transaction_service.patch_rollback_transaction(tx.id, db_session)
    bal_after = (await db_session.execute(select(UserBalance).where(UserBalance.id == bal.id))).scalar_one()

    assert bal_after.amount == Decimal("200")
    assert rolled.status == TransactionStatusEnum.ROLLBACKED


@pytest.mark.asyncio
async def test_double_rollback(db_session, usd_balance):
    user = await user_service.create_user(RequestUserModel(email=uniq_email("dbrlb"), password="x"), db_session)
    await usd_balance(user.id, 0)

    tx = await transaction_service.create_transaction(
        db_session,
        user.id,
        RequestTransactionModel(amount=10, currency=CurrencyEnum.USD, type=TransactionTypeEnum.DEPOSIT),
    )

    await transaction_service.patch_rollback_transaction(tx.id, db_session)
    with pytest.raises(TransactionAlreadyRollbackedException):
        await transaction_service.patch_rollback_transaction(tx.id, db_session)


@pytest.mark.asyncio
async def test_rollback_invalid_id(db_session):
    with pytest.raises(TransactionNotExistsException):
        await transaction_service.patch_rollback_transaction(9999, db_session)


@pytest.mark.asyncio
async def test_rollback_blocked_user(db_session, usd_balance):
    user = await user_service.create_user(RequestUserModel(email=uniq_email("rlbckblck"), password="x"), db_session)
    await usd_balance(user.id, 50)

    tx = await transaction_service.create_transaction(
        db_session,
        user.id,
        RequestTransactionModel(amount=10, currency=CurrencyEnum.USD.value, type=TransactionTypeEnum.WITHDRAWAL),
    )

    user.status = UserStatusEnum.BLOCKED
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(UpdateTransactionForBlockedUserException):
        await transaction_service.patch_rollback_transaction(tx.id, db_session)
