from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.db_models import Transaction, User
from ..schemas.python_models import CurrencyEnum

EXCHANGE_RATES_TO_USD = {
    CurrencyEnum.USD: 1,
    CurrencyEnum.EUR: 0.9342,
    CurrencyEnum.AUD: 0.5447,
    CurrencyEnum.CAD: 0.6162,
    CurrencyEnum.ARS: 0.0009,
    CurrencyEnum.PLN: 0.2343,
    CurrencyEnum.BTC: 100000.0,
    CurrencyEnum.ETH: 3557.3476,
    CurrencyEnum.DOGE: 0.3627,
    CurrencyEnum.USDT: 0.9709,
}


async def get_registered_users_count(session: AsyncSession, dt_gt: date, dt_lt: date):
    q = select(User).where((func.date(User.created >= dt_gt)) & (func.date(User.created) <= dt_lt))
    registered_users = await session.execute(q)
    registered_users = registered_users.fetchall()
    return len(registered_users)


async def get_registered_and_deposit_users_count(session: AsyncSession, dt_gt: date, dt_lt: date):
    result = 0
    q = select(User).where((func.date(User.created) >= dt_gt) & (func.date(User.created) <= dt_lt))
    registered_users = await session.execute(q)
    registered_users = registered_users.scalars()
    for user in registered_users:
        q = select(Transaction).where(
            (func.date(Transaction.created) >= dt_gt)
            & (func.date(Transaction.created) <= dt_lt)
            & (Transaction.user_id == user.id)
            & (Transaction.amount > 0)
        )
        deposits = await session.execute(q)
        deposits = deposits.fetchall()
        if len(deposits) > 0:
            result += 1
    return result


async def get_registered_and_not_rollbacked_deposit_users_count(session: AsyncSession, dt_gt: date, dt_lt: date):
    result = 0
    q = select(User).where((func.date(User.created >= dt_gt)) & (func.date(User.created) <= dt_lt))
    registered_users = await session.execute(q)
    registered_users = registered_users.scalars()
    for user in registered_users:
        q = select(Transaction).where(
            (func.date(Transaction.created) >= dt_gt)
            & (func.date(Transaction.created) <= dt_lt)
            & (Transaction.user_id == user.id)
            & (Transaction.amount > 0)
            & (Transaction.status != "ROLLBACKED")
        )
        not_rollbacked_deposits = await session.execute(q)
        not_rollbacked_deposits = not_rollbacked_deposits.fetchall()
        if len(not_rollbacked_deposits) > 0:
            result += 1
    return result


async def get_not_rollbacked_deposit_amount(session: AsyncSession, dt_gt: date, dt_lt: date):
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.amount > 0)
        & (Transaction.status != "ROLLBACKED")
    )
    not_rollbacked_deposits = await session.execute(q)
    not_rollbacked_deposits = not_rollbacked_deposits.scalars()
    return sum([x.amount * EXCHANGE_RATES_TO_USD[x.currency] for x in not_rollbacked_deposits])


async def get_not_rollbacked_withdraw_amount(session: AsyncSession, dt_gt: date, dt_lt: date):
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.amount < 0)
        & (Transaction.status != "ROLLBACKED")
    )
    not_rollbacked_withdraws = await session.execute(q)
    not_rollbacked_withdraws = not_rollbacked_withdraws.scalars()
    return sum([x.amount * EXCHANGE_RATES_TO_USD[x.currency] for x in not_rollbacked_withdraws])


async def get_transactions_count(session: AsyncSession, dt_gt: date, dt_lt: date):
    q = select(Transaction).where((func.date(Transaction.created) >= dt_gt) & (func.date(Transaction.created) <= dt_lt))
    transactions = await session.execute(q)
    transactions = transactions.fetchall()
    return len(transactions)


async def get_not_rollbacked_transactions_count(session: AsyncSession, dt_gt: date, dt_lt: date):
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.status != "ROLLBACKED")
    )
    transactions = await session.execute(q)
    transactions = transactions.fetchall()
    return len(transactions)
