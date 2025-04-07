import json
import random
from datetime import datetime, timedelta

from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery import celery_app
from app.config import REDIS_URL
from app.db.sessions import async_session_maker, get_async_session
from app.exceptions.exceptions import (ReportEnqueueException,
                                       ReportGenerationFailedException)
from app.schemas.enums import (CurrencyEnum, TransactionStatusEnum,
                               TransactionTypeEnum, UserStatusEnum)
from app.schemas.transaction_schemas import RequestTransactionModel
from app.schemas.user_schemas import RequestUserModel
from app.services.exchange_service import create_exchange_transaction
from app.services.transaction_service import create_transaction
from app.services.user_service import create_user

redis_cache = Redis.from_url(REDIS_URL, db=1)

router = APIRouter()


@router.get("/reports/weekly/json")
async def get_weekly_report_json():
    cached_data = redis_cache.get("weekly_report_json")
    if cached_data:
        data = json.loads(cached_data)
        return {"report": data}
    else:
        try:
            task = celery_app.send_task("generate_weekly_report")
        except Exception as e:
            raise ReportEnqueueException(f"Failed to enqueue report generation: {str(e)}")
        return JSONResponse(content={"task_id": task.id, "status": "processing"}, status_code=202)


@router.get("/reports/weekly/excel")
async def download_weekly_report_excel():
    excel_data = redis_cache.get("weekly_report_excel")
    if excel_data:
        headers = {"Content-Disposition": 'attachment; filename="weekly_report.xlsx"'}
        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    else:
        try:
            task = celery_app.send_task("generate_weekly_report")
        except Exception as e:
            raise ReportEnqueueException(f"Failed to enqueue report generation: {str(e)}")
        return JSONResponse(content={"task_id": task.id, "status": "processing"}, status_code=202)


@router.get("/reports/weekly/status/{task_id}")
def get_report_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    if result.state == "SUCCESS":
        cached_data = redis_cache.get("weekly_report_json")
        if cached_data:
            data = json.loads(cached_data)
            return {"task_id": task_id, "status": "completed", "report": data}
        else:
            return {"task_id": task_id, "status": "completed", "report": None}
    elif result.state in ["PENDING", "STARTED"]:
        return {"task_id": task_id, "status": result.state.lower()}
    elif result.state == "FAILURE":
        raise ReportGenerationFailedException("Report generation failed")
    else:
        return {"task_id": task_id, "status": result.state.lower()}


def generate_random_datetime(start: datetime, end: datetime) -> datetime:
    """Returns a random datetime between 'start' and 'end'."""
    delta = end - start
    random_seconds = random.uniform(0, delta.total_seconds())
    return start + timedelta(seconds=random_seconds)


@router.post("/populate")
async def populate_db(
    num_users: int = 100,
    deposit_probability: float = 0.7,
    withdrawal_probability: float = 0.5,
    transfer_probability: float = 0.3,
    exchange_probability: float = 0.2,
    cancel_probability: float = 0.1,
    block_probability: float = 0.1,
    min_amount: float = 10.0,
    max_amount: float = 1000.0,
    session: AsyncSession = Depends(get_async_session),
):
    users = []
    now = datetime.utcnow()
    reg_start = now - timedelta(days=360)  # roughly the last year

    # Create users via create_user
    for i in range(num_users):
        email = f"user{i}_{random.randint(1000, 9999)}@example.com"
        password = "password"
        new_user = await create_user(RequestUserModel(email=email, password=password), session)
        reg_date = generate_random_datetime(reg_start, now)
        new_user.created = reg_date
        if random.random() < block_probability:
            new_user.status = UserStatusEnum.BLOCKED.value
        session.add(new_user)
        users.append(new_user)
    await session.commit()

    user_ids = [u.id for u in users]
    created_transactions = []

    for user in users:
        if user.status != UserStatusEnum.ACTIVE.value:
            continue

        txn_start = user.created
        txn_end = now

        async def safe_create_transaction(create_func, *args, **kwargs):
            async with async_session_maker() as new_session:
                try:
                    txn = await create_func(new_session, *args, **kwargs)
                    txn.created = generate_random_datetime(txn_start, txn_end)
                    if random.random() < cancel_probability:
                        txn.status = TransactionStatusEnum.ROLLBACKED.value
                    await new_session.commit()
                    return txn
                except Exception:
                    await new_session.rollback()
                    return None

        def get_random_count():
            return random.randint(1, 3)

        # Deposit
        if random.random() < deposit_probability:
            for _ in range(get_random_count()):
                amount = round(random.uniform(min_amount, max_amount), 2)
                currency = random.choice(list(CurrencyEnum))
                deposit_data = RequestTransactionModel(
                    currency=currency,
                    amount=amount,
                    type=TransactionTypeEnum.DEPOSIT,
                )
                txn = await safe_create_transaction(create_transaction, user.id, deposit_data)
                if txn:
                    created_transactions.append(txn)

        # Withdrawal
        if random.random() < withdrawal_probability:
            for _ in range(get_random_count()):
                amount = round(random.uniform(min_amount, max_amount), 2)
                currency = random.choice(list(CurrencyEnum))
                withdrawal_data = RequestTransactionModel(
                    currency=currency,
                    amount=amount,
                    type=TransactionTypeEnum.WITHDRAWAL,
                )
                txn = await safe_create_transaction(create_transaction, user.id, withdrawal_data)
                if txn:
                    created_transactions.append(txn)

        # Transfer
        if random.random() < transfer_probability and len(user_ids) > 1:
            for _ in range(get_random_count()):
                possible_recipients = [uid for uid in user_ids if uid != user.id]
                recipient_id = random.choice(possible_recipients)
                amount = round(random.uniform(min_amount, max_amount), 2)
                currency = random.choice(list(CurrencyEnum))
                transfer_data = RequestTransactionModel(
                    currency=currency,
                    amount=amount,
                    type=TransactionTypeEnum.TRANSFER,
                    recipient_id=recipient_id,
                )
                txn = await safe_create_transaction(create_transaction, user.id, transfer_data)
                if txn:
                    created_transactions.append(txn)

        # Exchange
        if random.random() < exchange_probability:
            for _ in range(get_random_count()):
                from_currency, to_currency = random.sample(list(CurrencyEnum), 2)
                amount = round(random.uniform(min_amount, max_amount), 2)
                txn = await safe_create_transaction(
                    create_exchange_transaction, user.id, from_currency, to_currency, amount
                )
                if txn:
                    created_transactions.append(txn)

    return {"detail": f"Populated DB with {num_users} users and {len(created_transactions)} transactions."}
