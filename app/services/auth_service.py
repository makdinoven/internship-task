from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import JWT_ALGORITHM, JWT_EXPIRATION_MINUTES, JWT_SECRET
from app.exceptions.exceptions import (InvalidTokenException,
                                       TokenExpiredException)
from app.models.db_models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
    user_query = await session.execute(select(User).where(User.email == email))
    user = user_query.scalar()
    if not user or not pwd_context.verify(password, user.password):
        return None
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRATION_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredException
    except InvalidTokenError:
        raise InvalidTokenException
