from datetime import timedelta

import uvicorn
from fastapi import Depends, FastAPI, status
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from .config import DATABASE_URL
from .exceptions.exceptions import (BadRequestDataException,
                                    CreateTransactionForBlockedUserException,
                                    NegativeBalanceException,
                                    TransactionAlreadyRollbackedException,
                                    TransactionDoesNotBelongToUserException,
                                    TransactionNotExistsException,
                                    UpdateTransactionForBlockedUserException,
                                    UserAlreadyActiveException,
                                    UserAlreadyBlockedException,
                                    UserAlreadyExistsException,
                                    UserNotExistsException)
from .models.db_models import *
from .schemas.python_models import *
from .services.queries import (
    get_not_rollbacked_deposit_amount, get_not_rollbacked_transactions_count,
    get_not_rollbacked_withdraw_amount, get_registered_and_deposit_users_count,
    get_registered_and_not_rollbacked_deposit_users_count,
    get_registered_users_count, get_transactions_count)

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> typing.AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


app = FastAPI()


@app.on_event("startup")
async def on_startup(session: AsyncSession = Depends(get_async_session)):
    await create_db_and_tables()


@app.get("/users", response_model=typing.Optional[list[ResponseUserModel]] | None, status_code=status.HTTP_200_OK)
async def get_users(
    user_id: typing.Optional[int] = None,
    email: typing.Optional[str] = None,
    user_status: typing.Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
) -> typing.List[ResponseUserModel]:
    q = select(User).order_by(User.created.desc())
    if user_id is not None:
        q = q.where(User.id == user_id)
    if email is not None:
        q = q.where(User.email == email)
    if user_status is not None:
        q = q.where(User.status == user_status)
    users = await session.execute(q)
    users = users.scalars()
    results = []
    for user in users:
        result = ResponseUserModel(
            id=user.id, email=user.email, status=UserStatusEnum(user.status), created=user.created
        )
        balances = await session.execute(select(UserBalance).where(UserBalance.user_id == user.id))
        balances = balances.scalars()
        balances = sorted([{"currency": b.currency, "amount": b.amount} for b in balances], key=lambda x: x["amount"])
        result.balances = balances
        results.append(result)
    return sorted(results, key=lambda x: x.created)


@app.post("/users", status_code=status.HTTP_200_OK)
async def post_user(user: RequestUserModel, session: AsyncSession = Depends(get_async_session)):
    email = user.email.strip()
    email = "".join([x for x in email if x != " "])
    if len(email) == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email can't consist entirely of spaces"
        )
    db_user = await session.execute(select(User).where(User.email == user.email))
    if db_user.scalar():
        raise UserAlreadyExistsException(
            status_code=status.HTTP_409_CONFLICT, detail="User with email=`{0}` already exists".format(user.email)
        )
    db_user = User(email=user.email, status="ACTIVE", created=datetime.utcnow())
    session.add(db_user)
    await session.commit()
    currencies = list({str(x) for x in CurrencyEnum})
    for currency in currencies:
        user_balance = UserBalance(user_id=db_user.id, currency=currency, amount=0, created=datetime.utcnow())
        session.add(user_balance)
        await session.commit()
    result = await session.execute(select(User).where(User.email == user.email))
    result = result.scalar()
    result = UserModel(id=result.id, email=result.email, status=UserStatusEnum(result.status), created=result.created)
    return result


@app.patch("/users/{user_id}", response_model=typing.Optional[UserModel] | None)
async def patch_user(user_id: int, user: RequestUserUpdateModel, session: AsyncSession = Depends(get_async_session)):
    if user_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unprocessable data in request"
        )
    db_user = await session.execute(select(User).where(User.id == user_id))
    db_user = db_user.scalar()
    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User with id=`{0}` does not exist".format(user_id)
        )
    if db_user.status == "BLOCKED" and user.status == "BLOCKED":
        raise UserAlreadyBlockedException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User with id=`{0}` is already blocked".format(user_id)
        )
    if db_user.status == "ACTIVE" and user.status == "ACTIVE":
        raise UserAlreadyActiveException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User with id=`{0}` is already active".format(user_id)
        )
    await session.execute(update(User).values(**{"status": user.status}).where(User.id == user_id))
    await session.commit()
    user = await session.execute(select(User).where(User.id == user_id))
    user = user.scalar()
    result = UserModel(id=user.id, email=user.email, status=UserStatusEnum(user.status), created=user.created)
    return result


@app.get("/transactions", response_model=typing.Optional[list[TransactionModel]] | None, status_code=status.HTTP_200_OK)
async def get_transactions(
    user_id: typing.Optional[int] = None, session: AsyncSession = Depends(get_async_session)
) -> typing.List[TransactionModel]:
    q = select(Transaction).order_by(Transaction.created.desc())
    if user_id:
        q = q.where(Transaction.user_id == user_id)

    transactions = await session.execute(q)
    transactions = transactions.scalars()
    results = []
    for t in transactions:
        result = TransactionModel(
            **{
                "id": t.id,
                "user_id": t.user_id,
                "currency": CurrencyEnum(t.currency),
                "amount": t.amount,
                "status": TransactionStatusEnum(t.status),
                "created": t.created,
            }
        )
        results.append(result)
    return results


@app.post("/{user_id}/transactions", response_model=typing.Optional[TransactionModel] | None, status_code=status.HTTP_200_OK)
async def post_transaction(
    user_id: int, transaction: RequestTransactionModel, session: AsyncSession = Depends(get_async_session)
):
    if user_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unprocessable data in request"
        )
    if transaction.currency not in {str(x) for x in CurrencyEnum}:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Currency does not exist"
        )
    if transaction.amount == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Transaction can not have zero amount"
        )

    db_user = await session.execute(select(User).where(User.id == user_id))
    db_user = db_user.scalar()
    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User with id=`{0}` does not exist".format(user_id)
        )
    if db_user.status != "ACTIVE":
        raise CreateTransactionForBlockedUserException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User with id=`{0}` is blocked".format(user_id)
        )

    db_user_balance = await session.execute(
        select(UserBalance).where((UserBalance.user_id == user_id) & (UserBalance.currency == transaction.currency))
    )
    db_user_balance = db_user_balance.scalar()
    if float(db_user_balance.amount) + transaction.amount < 0:
        raise NegativeBalanceException(status_code=status.HTTP_400_BAD_REQUEST, detail="Negative balance")

    await session.execute(
        update(UserBalance).values(**{"amount": transaction.amount}).where(UserBalance.id == db_user_balance.id)
    )
    await session.commit()
    await session.execute(
        insert(Transaction).values(
            **{
                "user_id": db_user.id,
                "currency": transaction.currency,
                "amount": transaction.amount,
                "status": "PROCESSED",
                "created": datetime.utcnow(),
            }
        )
    )
    await session.commit()


@app.patch("/{user_id}/transactions/{transaction_id}", response_model=typing.Optional[TransactionModel] | None)
async def patch_rollback_transaction(
    user_id: int, transaction_id: int, session: AsyncSession = Depends(get_async_session)
):
    if user_id < 0 or transaction_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unprocessable data in request"
        )
    db_user = await session.execute(select(User).where(User.id == user_id))
    db_user = db_user.scalar()
    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User with id=`{0}` does not exist".format(user_id)
        )
    db_transaction = await session.execute(select(Transaction).where(Transaction.id == transaction_id))
    db_transaction = db_transaction.scalar()
    if not db_transaction:
        raise TransactionNotExistsException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction with id=`{0}` does not exist".format(transaction_id),
        )
    if db_transaction.user_id != db_user.id:
        raise TransactionDoesNotBelongToUserException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction with id=`{0}` does not belong to user with id=`{1}`".format(transaction_id, user_id),
        )
    if db_transaction.status == "ROLLBACKED":
        raise TransactionAlreadyRollbackedException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction with id=`{0}` is already rollbacked".format(transaction_id),
        )
    if db_user.status == "BLOCKED":
        raise UpdateTransactionForBlockedUserException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User with id=`{0}` is blocked".format(user_id)
        )

    db_user_balance = await session.execute(
        select(UserBalance).where((UserBalance.user_id == user_id) & (UserBalance.currency == db_transaction.currency))
    )
    db_user_balance = db_user_balance.scalar()
    new_amount = float(db_user_balance.amount)
    if db_transaction.amount < 0:
        new_amount += abs(float(db_transaction.amount))
    else:
        new_amount -= float(db_transaction.amount)
    if new_amount < 0:
        raise NegativeBalanceException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Negative balance: {new_amount}"
        )
    await session.execute(
        update(UserBalance).values(**{"amount": new_amount}).where(UserBalance.id == db_user_balance.id)
    )
    await session.commit()
    await session.execute(update(Transaction).values(**{"status": "ROLLBACKED"}))
    await session.commit()


@app.get("/transactions/analysis", response_model=typing.Optional[list] | None, status_code=status.HTTP_200_OK)
async def get_transaction_analysis(session: AsyncSession = Depends(get_async_session)) -> typing.List[dict]:
    dt_gt = datetime.utcnow().date() - timedelta(weeks=1) + timedelta(days=1)
    dt_lt = datetime.utcnow().date()
    results = []
    for i in range(52):
        registered_users_count = await get_registered_users_count(session, dt_gt=dt_gt, dt_lt=dt_lt)
        registered_and_deposit_users_count = await get_registered_and_deposit_users_count(
            session, dt_gt=dt_gt, dt_lt=dt_lt
        )
        registered_and_not_rollbacked_deposit_users_count = await get_registered_and_not_rollbacked_deposit_users_count(
            session, dt_gt=dt_gt, dt_lt=dt_lt
        )
        not_rollbacked_deposit_amount = await get_not_rollbacked_deposit_amount(session, dt_gt=dt_gt, dt_lt=dt_lt)
        not_rollbacked_withdraw_amount = await get_not_rollbacked_withdraw_amount(session, dt_gt=dt_gt, dt_lt=dt_lt)
        transactions_count = await get_transactions_count(session, dt_gt=dt_gt, dt_lt=dt_lt)
        not_rollbacked_transactions_count = await get_not_rollbacked_transactions_count(
            session, dt_gt=dt_gt, dt_lt=dt_lt
        )
        result = {
            "start_date": dt_gt,
            "end_date": dt_lt,
            "registered_users_count": registered_users_count,
            "registered_and_deposit_users_count": registered_and_deposit_users_count,
            "registered_and_not_rollbacked_deposit_users_count": registered_and_not_rollbacked_deposit_users_count,
            "not_rollbacked_deposit_amount": not_rollbacked_deposit_amount,
            "not_rollbacked_withdraw_amount": not_rollbacked_withdraw_amount,
            "transactions_count": transactions_count,
            "not_rollbacked_transactions_count": not_rollbacked_transactions_count,
        }
        for field in (
            "registered_users_count",
            "registered_and_deposit_users_count",
            "registered_and_not_rollbacked_deposit_users_count",
            "not_rollbacked_deposit_amount",
            "not_rollbacked_withdraw_amount",
            "transactions_count",
            "not_rollbacked_transactions_count",
        ):
            if result[field] > 0:
                results.append(result)
                break
        dt_gt -= timedelta(weeks=1)
        dt_lt -= timedelta(weeks=1)
    return results


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7999, reload=True)
