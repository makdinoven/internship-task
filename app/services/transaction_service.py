import typing
from decimal import Decimal

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.exceptions import (
    BadRequestDataException, CreateTransactionForBlockedUserException,
    NegativeBalanceException, TransactionAlreadyRollbackedException,
    TransactionNotExistsException, UpdateTransactionForBlockedUserException,
    UserNotExistsException)
from app.models.db_models import Transaction, User, UserBalance
from app.schemas.enums import (TransactionDirectionEnum, TransactionStatusEnum,
                               TransactionTypeEnum, UserStatusEnum)
from app.schemas.transaction_schemas import (RequestTransactionModel,
                                             TransactionModel)


async def get_transactions(
    user_id: typing.Optional[int],
    session: AsyncSession,
    direction: typing.Optional[TransactionDirectionEnum] = None,
) -> typing.List[TransactionModel]:
    query = select(Transaction).order_by(Transaction.created.desc())
    if user_id is not None:
        if direction == "received":
            query = query.where(
                or_(
                    and_(Transaction.type == TransactionTypeEnum.DEPOSIT.value, Transaction.sender_id == user_id),
                    and_(Transaction.type == TransactionTypeEnum.TRANSFER.value, Transaction.recipient_id == user_id),
                )
            )
        elif direction == "sent":
            query = query.where(
                or_(
                    and_(Transaction.type == TransactionTypeEnum.WITHDRAWAL.value, Transaction.sender_id == user_id),
                    and_(Transaction.type == TransactionTypeEnum.TRANSFER.value, Transaction.sender_id == user_id),
                )
            )
        else:
            query = query.where(or_(Transaction.sender_id == user_id, Transaction.recipient_id == user_id))

    result = await session.execute(query)
    transactions = result.scalars().all()
    return [TransactionModel.model_validate(t) for t in transactions]


async def create_transaction(
    session: AsyncSession,
    sender_id: int,
    transaction_data: RequestTransactionModel,
) -> Transaction:
    if sender_id < 0:
        raise BadRequestDataException(detail="Sender id must be positive")
    if transaction_data.amount <= 0:
        raise BadRequestDataException(detail="Amount must be positive")

    amount = Decimal(transaction_data.amount)

    result = await session.execute(select(User).where(User.id == sender_id))
    sender = result.scalar()
    if not sender:
        raise UserNotExistsException(user_id=sender_id)
    if sender.status != UserStatusEnum.ACTIVE:
        raise CreateTransactionForBlockedUserException(user_id=sender_id)

    result = await session.execute(
        select(UserBalance).where(
            (UserBalance.user_id == sender_id) & (UserBalance.currency == transaction_data.currency)
        )
    )
    sender_balance = result.scalar()
    if not sender_balance:
        raise BadRequestDataException(detail="Sender balance not found")

    if transaction_data.type == TransactionTypeEnum.TRANSFER:
        if transaction_data.recipient_id is None:
            raise BadRequestDataException(detail="Recipient id must be provided for transfer.")

        result = await session.execute(select(User).where(User.id == transaction_data.recipient_id))
        recipient = result.scalar()
        if not recipient:
            raise UserNotExistsException(user_id=transaction_data.recipient_id)
        if recipient.status != UserStatusEnum.ACTIVE:
            raise CreateTransactionForBlockedUserException(user_id=transaction_data.recipient_id)

        result = await session.execute(
            select(UserBalance).where(
                (UserBalance.user_id == transaction_data.recipient_id)
                & (UserBalance.currency == transaction_data.currency)
            )
        )
        recipient_balance = result.scalar()
        if not recipient_balance:
            raise BadRequestDataException(detail="Recipient balance not found")

        if sender_balance.amount < amount:
            raise NegativeBalanceException(balance=sender_balance.amount)

        sender_balance.amount -= amount
        recipient_balance.amount += amount

        new_transaction = Transaction(
            sender_id=sender_id,
            recipient_id=transaction_data.recipient_id,
            currency=transaction_data.currency,
            amount=amount,
            type=TransactionTypeEnum.TRANSFER.value,
            status=TransactionStatusEnum.PROCESSED.value,
        )

    elif transaction_data.type == TransactionTypeEnum.DEPOSIT:
        sender_balance.amount += amount
        new_transaction = Transaction(
            sender_id=sender_id,
            currency=transaction_data.currency,
            amount=amount,
            type=TransactionTypeEnum.DEPOSIT.value,
            status=TransactionStatusEnum.PROCESSED.value,
        )

    elif transaction_data.type == TransactionTypeEnum.WITHDRAWAL:
        if sender_balance.amount < amount:
            raise NegativeBalanceException(balance=sender_balance.amount)
        sender_balance.amount -= amount
        new_transaction = Transaction(
            sender_id=sender_id,
            currency=transaction_data.currency,
            amount=amount,
            type=TransactionTypeEnum.WITHDRAWAL.value,
            status=TransactionStatusEnum.PROCESSED.value,
        )

    else:
        raise BadRequestDataException(detail="Invalid transaction type")

    session.add(new_transaction)
    await session.commit()
    await session.refresh(new_transaction)
    return new_transaction


async def patch_rollback_transaction(transaction_id: int, session: AsyncSession):
    if transaction_id < 0:
        raise BadRequestDataException(detail="transaction_id must be positive")

    db_transaction_query = await session.execute(select(Transaction).where(Transaction.id == transaction_id))
    db_transaction = db_transaction_query.scalar()
    if not db_transaction:
        raise TransactionNotExistsException(transaction_id=transaction_id)

    if db_transaction.status == TransactionStatusEnum.ROLLBACKED.value:
        raise TransactionAlreadyRollbackedException(transaction_id=transaction_id)

    sender_user_query = await session.execute(select(User).where(User.id == db_transaction.sender_id))
    sender_user = sender_user_query.scalar()
    if not sender_user:
        raise UserNotExistsException(user_id=db_transaction.sender_id)
    if sender_user.status != UserStatusEnum.ACTIVE.value:
        raise UpdateTransactionForBlockedUserException(user_id=db_transaction.sender_id)

    if db_transaction.type == TransactionTypeEnum.TRANSFER.value:
        recipient_user_query = await session.execute(select(User).where(User.id == db_transaction.recipient_id))
        recipient_user = recipient_user_query.scalar()
        if not recipient_user:
            raise UserNotExistsException(user_id=db_transaction.recipient_id)
        if recipient_user.status != UserStatusEnum.ACTIVE.value:
            raise UpdateTransactionForBlockedUserException(user_id=db_transaction.recipient_id)

    t_amount = Decimal(db_transaction.amount)

    if db_transaction.type == TransactionTypeEnum.DEPOSIT.value:
        balance_query = await session.execute(
            select(UserBalance).where(
                (UserBalance.user_id == db_transaction.sender_id) & (UserBalance.currency == db_transaction.currency)
            )
        )
        balance = balance_query.scalar()
        if not balance:
            raise BadRequestDataException(detail="Balance not found")
        if balance.amount < t_amount:
            raise NegativeBalanceException(balance=balance.amount)
        balance.amount -= t_amount

    elif db_transaction.type == TransactionTypeEnum.WITHDRAWAL.value:
        balance_query = await session.execute(
            select(UserBalance).where(
                (UserBalance.user_id == db_transaction.sender_id) & (UserBalance.currency == db_transaction.currency)
            )
        )
        sender_balance = balance_query.scalar()
        if not sender_balance:
            raise BadRequestDataException(detail="Balance not found")
        sender_balance.amount += t_amount

    elif db_transaction.type == TransactionTypeEnum.TRANSFER.value:
        sender_balance_query = await session.execute(
            select(UserBalance).where(
                (UserBalance.user_id == db_transaction.sender_id) & (UserBalance.currency == db_transaction.currency)
            )
        )
        sender_balance = sender_balance_query.scalar()
        if not sender_balance:
            raise BadRequestDataException(detail="Sender balance not found")
        sender_balance.amount += t_amount
        recipient_balance_query = await session.execute(
            select(UserBalance).where(
                (UserBalance.user_id == db_transaction.recipient_id) & (UserBalance.currency == db_transaction.currency)
            )
        )
        recipient_balance = recipient_balance_query.scalar()
        if not recipient_balance:
            raise BadRequestDataException(detail="Recipient balance not found")
        if recipient_balance.amount < t_amount:
            raise NegativeBalanceException(balance=recipient_balance.amount)
        recipient_balance.amount -= t_amount

    else:
        raise BadRequestDataException(detail="Unknown transaction type")

    await session.execute(
        update(Transaction)
        .where(Transaction.id == transaction_id)
        .values(status=TransactionStatusEnum.ROLLBACKED.value)
    )

    await session.commit()

    updated_transaction_query = await session.execute(select(Transaction).where(Transaction.id == transaction_id))
    updated_transaction = updated_transaction_query.scalar()
    return TransactionModel.model_validate(updated_transaction)
