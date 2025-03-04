import json
from decimal import Decimal

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import REDIS_URL
from app.exceptions.exceptions import (BadRequestDataException,
                                       CurrencyRateFetchException,
                                       NegativeBalanceException)
from app.models.db_models import Transaction, UserBalance
from app.schemas.enums import (CurrencyEnum, TransactionStatusEnum,
                               TransactionTypeEnum)

_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        # Initialize Redis client (singleton)
        _redis_client = aioredis.from_url(REDIS_URL)
    return _redis_client


async def get_cached_rates_for_base(base: str) -> dict:
    client = get_redis_client()
    cache_key = f"rates:{base}"
    data = await client.get(cache_key)
    if data:
        try:
            return json.loads(data)
        except Exception as e:
            raise CurrencyRateFetchException(detail=f"Error decoding cache for {base}: {e}")

    # Fallback: trigger update if cache is empty or invalid
    from app.tasks.update_rates import update_rates

    update_result = update_rates()
    if update_result != "Success":
        raise CurrencyRateFetchException(detail="Failed to update rates during fallback")

    data = await client.get(cache_key)
    if data:
        try:
            return json.loads(data)
        except Exception as e:
            raise CurrencyRateFetchException(detail=f"Error decoding cache after update for {base}: {e}")

    raise CurrencyRateFetchException(detail="Unable to retrieve rates from cache after update")


async def create_exchange_transaction(
    session: AsyncSession, user_id: int, from_currency: CurrencyEnum, to_currency: CurrencyEnum, amount: float
) -> Transaction:
    if amount <= 0:
        raise BadRequestDataException(detail="Amount must be positive")

    # Retrieve user's balance for the source currency
    query_from = select(UserBalance).where(UserBalance.user_id == user_id, UserBalance.currency == from_currency.value)
    res_from = await session.execute(query_from)
    balance_from = res_from.scalar_one_or_none()
    if not balance_from:
        raise BadRequestDataException(detail=f"Balance for {from_currency.value} not found")
    if balance_from.amount < Decimal(amount):
        raise NegativeBalanceException(balance=balance_from.amount)

    # Retrieve user's balance for the target currency
    query_to = select(UserBalance).where(UserBalance.user_id == user_id, UserBalance.currency == to_currency.value)
    res_to = await session.execute(query_to)
    balance_to = res_to.scalar_one_or_none()
    if not balance_to:
        raise BadRequestDataException(detail=f"Balance for {to_currency.value} not found")

    # Get conversion rates from cache (or fallback to update)
    rates = await get_cached_rates_for_base(from_currency.value)
    if to_currency.value not in rates:
        raise BadRequestDataException(detail=f"Conversion rate for {to_currency.value} not available")

    conversion_rate = Decimal(rates[to_currency.value])
    converted_amount = Decimal(amount) * conversion_rate

    # Update balances
    balance_from.amount -= Decimal(amount)
    balance_to.amount += converted_amount

    # Record the transaction in the database
    new_transaction = Transaction(
        sender_id=user_id,
        recipient_id=user_id,
        currency=from_currency.value,
        amount=Decimal(amount),
        type=TransactionTypeEnum.EXCHANGE.value,
        from_currency=from_currency.value,
        to_currency=to_currency.value,
        status=TransactionStatusEnum.PROCESSED.value,
    )
    session.add(new_transaction)
    await session.commit()
    await session.refresh(new_transaction)
    return new_transaction
