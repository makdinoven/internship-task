import json
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.exceptions.exceptions import (BadRequestDataException,
                                       CurrencyRateFetchException,
                                       NegativeBalanceException)
from app.models.db_models import Transaction, UserBalance
from app.schemas.enums import (CurrencyEnum, TransactionStatusEnum,
                               TransactionTypeEnum)
from app.schemas.user_schemas import RequestUserModel
from app.services import exchange_service, user_service
from app.tests.utils_test import uniq_email


async def _set_balance(session, user_id: int, currency: CurrencyEnum, amount: Decimal):
    q = select(UserBalance).where(
        UserBalance.user_id == user_id,
        UserBalance.currency == currency.value,
    )
    bal = (await session.execute(q)).scalar_one_or_none()
    if bal:
        bal.amount = amount
    else:
        session.add(UserBalance(user_id=user_id, currency=currency.value, amount=amount))
    await session.flush()


class _FakeRedis:  # минимальный in‑memory клон aioredis
    def __init__(self):
        self._store: dict[str, bytes] = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value: bytes):
        self._store[key] = value

    async def setex(self, key, ttl, value):
        self._store[key] = value


@pytest.fixture
def fake_redis(monkeypatch):
    client = _FakeRedis()
    # подменяем функцию в сервисе обмена
    monkeypatch.setattr(exchange_service, "get_redis_client", lambda: client)
    # сбрасываем «старый» кеш, если он был инициализирован
    monkeypatch.setattr(exchange_service, "_redis_client", None, raising=False)
    return client


@pytest.mark.asyncio
async def test_successful_exchange(db_session, fake_redis):
    """USD to EUR: баланс списывается/зачисляется, транзакция создаётся."""
    await fake_redis.set("rates:USD", json.dumps({"EUR": "0.9"}).encode())

    user = await user_service.create_user(RequestUserModel(email=uniq_email("ex_ok"), password="p"), db_session)

    await _set_balance(db_session, user.id, CurrencyEnum.USD, Decimal(200))
    await _set_balance(db_session, user.id, CurrencyEnum.EUR, Decimal(0))

    tx = await exchange_service.create_exchange_transaction(
        db_session, user.id, CurrencyEnum.USD, CurrencyEnum.EUR, 100
    )

    #  проверки
    assert isinstance(tx, Transaction)
    assert tx.type == TransactionTypeEnum.EXCHANGE.value
    assert tx.status == TransactionStatusEnum.PROCESSED.value

    balances = (await db_session.execute(select(UserBalance).where(UserBalance.user_id == user.id))).scalars().all()
    usd = next(b for b in balances if b.currency == CurrencyEnum.USD)
    eur = next(b for b in balances if b.currency == CurrencyEnum.EUR)
    assert usd.amount == Decimal("100")  # 200 – 100
    assert eur.amount == Decimal("90")  # 0 + 100*0.9


@pytest.mark.asyncio
async def test_insufficient_funds(db_session, fake_redis):
    await fake_redis.set("rates:USD", json.dumps({"EUR": "1"}).encode())
    user = await user_service.create_user(RequestUserModel(email=uniq_email("ex_nf"), password="p"), db_session)
    await _set_balance(db_session, user.id, CurrencyEnum.USD, Decimal(50))
    await _set_balance(db_session, user.id, CurrencyEnum.EUR, Decimal(0))

    with pytest.raises(NegativeBalanceException):
        await exchange_service.create_exchange_transaction(db_session, user.id, CurrencyEnum.USD, CurrencyEnum.EUR, 100)


@pytest.mark.asyncio
async def test_rate_not_available(db_session, fake_redis):
    await fake_redis.set("rates:USD", json.dumps({"GBP": "0.8"}).encode())  # EUR нет
    user = await user_service.create_user(RequestUserModel(email=uniq_email("ex_rate"), password="p"), db_session)
    await _set_balance(db_session, user.id, CurrencyEnum.USD, Decimal(100))
    await _set_balance(db_session, user.id, CurrencyEnum.EUR, Decimal(0))

    with pytest.raises(BadRequestDataException):
        await exchange_service.create_exchange_transaction(db_session, user.id, CurrencyEnum.USD, CurrencyEnum.EUR, 10)


@pytest.mark.asyncio
async def test_cache_miss_triggers_update(monkeypatch, fake_redis):
    """
    Кеша нет - вызывается update_rates, кладёт данные в Redis,
    get_cached_rates_for_base возвращает свежий словарь.
    """

    # заглушка update_rates, которая пишет курс в fake_redis
    def _stub_update_rates():
        fake_redis._store["rates:USD"] = json.dumps({"EUR": "0.95"}).encode()
        return "Success"

    # подменяем реальную функцию на заглушку
    monkeypatch.setattr("app.tasks.update_rates.update_rates", _stub_update_rates)

    rates = await exchange_service.get_cached_rates_for_base("USD")
    assert rates == {"EUR": "0.95"}

    # повторный вызов берёт данные уже из кеша
    cached = await exchange_service.get_cached_rates_for_base("USD")
    assert cached == {"EUR": "0.95"}


@pytest.mark.asyncio
async def test_cache_decode_error(monkeypatch, fake_redis):
    """Если в Redis лежат битые данные и update_rates падает ‒ получаем CurrencyRateFetchException."""
    await fake_redis.set("rates:USD", b"not-json")

    # update_rates «проваливается»
    monkeypatch.setattr("app.tasks.update_rates.update_rates", lambda: "Failure")

    with pytest.raises(CurrencyRateFetchException):
        await exchange_service.get_cached_rates_for_base("USD")
