import typing

from passlib.context import CryptContext
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions.exceptions import (BadRequestDataException,
                                       UserAlreadyActiveException,
                                       UserAlreadyBlockedException,
                                       UserAlreadyExistsException,
                                       UserNotExistsException)
from app.models.db_models import User, UserBalance
from app.schemas.enums import CurrencyEnum, UserRoleEnum, UserStatusEnum
from app.schemas.user_schemas import (RequestUserModel, RequestUserUpdateModel,
                                      ResponseUserBalanceModel,
                                      ResponseUserModel, UserModel)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_users(
    session: AsyncSession,
    user_id: typing.Optional[int] = None,
    email: typing.Optional[EmailStr] = None,
    user_status: typing.Optional[UserStatusEnum] = None,
) -> typing.List[ResponseUserModel]:

    query = select(User).options(selectinload(User.user_balance))

    if user_id is not None:
        query = query.where(User.id == user_id)
    if email is not None:
        query = query.where(User.email == email)
    if user_status is not None:
        query = query.where(User.status == user_status)

    users_query = await session.execute(query)
    users = users_query.scalars().all()

    result_users = []
    for user in users:
        sorted_balance = sorted(
            [
                ResponseUserBalanceModel(
                    currency=b.currency,
                    amount=b.amount,
                )
                for b in user.user_balance
            ],
            key=lambda b: b.amount,
        )
        result_users.append(
            ResponseUserModel(
                id=user.id,
                email=user.email,
                status=user.status,
                created=user.created,
                balances=sorted_balance,
            )
        )

    return result_users


async def create_user(user: RequestUserModel, session: AsyncSession):

    query_existing_user = await session.execute(select(User).where(User.email == user.email))
    existing_user = query_existing_user.scalar()
    if existing_user:
        raise UserAlreadyExistsException(email=str(user.email))
    hashed_password = pwd_context.hash(user.password)

    new_user = User(
        role=UserRoleEnum.USER,
        email=str(user.email),
        password=hashed_password,
        status=UserStatusEnum.ACTIVE,
    )
    session.add(new_user)
    await session.flush()
    wallets = [UserBalance(user_id=new_user.id, currency=curr, amount=0) for curr in CurrencyEnum]
    session.add_all(wallets)
    await session.commit()
    await session.refresh(new_user)
    return new_user


async def update_user_status(user_id: int, status_update: RequestUserUpdateModel, session: AsyncSession):
    if user_id < 0:
        raise BadRequestDataException(detail="Invalid user ID")
    db_user_query = await session.execute(select(User).where(User.id == user_id))
    db_user = db_user_query.scalar()

    if not db_user:
        raise UserNotExistsException(user_id=user_id)

    if db_user.status == status_update.status:
        if db_user.status == UserStatusEnum.BLOCKED:
            raise UserAlreadyBlockedException(user_id=user_id)
        elif db_user.status == UserStatusEnum.ACTIVE:
            raise UserAlreadyActiveException(user_id=user_id)

    db_user.status = status_update.status
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return UserModel.model_validate(db_user)


async def get_user_by_id(session: AsyncSession, user_id: int) -> ResponseUserModel:
    users = await get_users(session, user_id=user_id)
    if not users:
        raise UserNotExistsException(user_id=user_id)
    return users[0]
