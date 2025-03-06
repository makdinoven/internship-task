import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sessions import get_async_session
from app.dependencies import get_current_user
from app.exceptions.exceptions import (BadRequestDataException,
                                       CurrencyRateFetchException)
from app.schemas.enums import CurrencyEnum
from app.schemas.transaction_schemas import TransactionModel
from app.services.exchange_service import create_exchange_transaction
from app.tasks.update_rates import CURRENCIES, redis_client, update_rates

router = APIRouter()


@router.post("/exchange", response_model=TransactionModel, summary="Perform currency exchange")
async def post_exchange(
    from_currency: CurrencyEnum,
    to_currency: CurrencyEnum,
    amount: float = Query(..., gt=0, description="Amount"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    # Process exchange transaction and return its model
    try:
        transaction = await create_exchange_transaction(session, current_user.id, from_currency, to_currency, amount)
        return TransactionModel.model_validate(transaction)
    except (BadRequestDataException,) as exc:
        raise exc
    except Exception as e:
        raise BadRequestDataException(detail=str(e))


@router.get("/rates/{base}", summary="Get exchange rates")
def get_rates(base: str):
    base = base.upper()
    if base not in CURRENCIES:
        raise BadRequestDataException(detail="Base currency not supported")
    cache_key = f"rates:{base}"
    data = redis_client.get(cache_key)
    if data:
        return json.loads(data)
    # Fallback: update rates if not in cache
    update_rates()
    data = redis_client.get(cache_key)
    if data:
        return json.loads(data)
    else:
        raise CurrencyRateFetchException(detail="Unable to retrieve rates")
