from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sessions import get_async_session
from app.exceptions.exceptions import (InsufficientPrivilegesException,
                                       InvalidTokenException)
from app.schemas.enums import UserRoleEnum
from app.services.auth_service import decode_access_token
from app.services.user_service import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(session: AsyncSession = Depends(get_async_session), token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenException()
    return await get_user_by_id(session, int(user_id))


async def get_current_admin(current_user=Depends(get_current_user)):
    if current_user.role != UserRoleEnum.ADMIN:
        raise InsufficientPrivilegesException()
    return current_user
