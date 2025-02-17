import typing

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.sessions import get_async_session
from ..dependencies import get_current_admin, get_current_user
from ..exceptions.exceptions import InsufficientPrivilegesException
from ..schemas.enums import TransactionDirectionEnum, UserRoleEnum
from ..schemas.transaction_schemas import (RequestTransactionModel,
                                           TransactionModel)
from ..services import transaction_service

router = APIRouter()


@router.get(
    "/",
    response_model=typing.Optional[list[TransactionModel]] | None,
    status_code=status.HTTP_200_OK,
)
async def get_transactions(
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
    user_id: typing.Optional[int] = Query(None, description="For admins only"),
    direction: typing.Optional[TransactionDirectionEnum] = Query(None),
) -> typing.List[TransactionModel]:

    if current_user.role != UserRoleEnum.ADMIN:
        if user_id is not None and user_id != current_user.id:
            raise InsufficientPrivilegesException()
        target_user_id = current_user.id
    else:
        target_user_id = user_id

    return await transaction_service.get_transactions(target_user_id, session, direction)


@router.post("/", response_model=typing.Optional[TransactionModel] | None, status_code=status.HTTP_200_OK)
async def create_transaction(
    transaction: RequestTransactionModel,
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    return await transaction_service.create_transaction(session, current_user.id, transaction)


@router.patch("/{transaction_id}/rollback", response_model=TransactionModel)
async def patch_rollback_transaction(
    transaction_id: int, session: AsyncSession = Depends(get_async_session), admin=Depends(get_current_admin)
):
    return await transaction_service.patch_rollback_transaction(transaction_id, session)
