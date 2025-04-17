import asyncio
import os
import tempfile
import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.sessions import get_async_session
from app.main import app
from app.models.db_models import Base, User
from app.services import auth_service
from app.services.auth_service import pwd_context

fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.chmod(db_path, 0o666)

TEST_DB_URL = f"sqlite+aiosqlite:///{db_path}"
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

engine = create_async_engine(TEST_DB_URL, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore


async def async_create_all():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Создаем таблицы в новой тестовой БД
asyncio.run(async_create_all())


# Переопределяем зависимость get_db для FastAPI, чтобы использовать тестовую БД
async def override_get_db():
    async with AsyncSessionLocal() as session:
        # Создаем новую сессию на время запроса
        yield session
        # Откатываем изменения после запроса (чтобы тесты были изолированы, если не вызвать commit)
        await session.rollback()


app.dependency_overrides[get_async_session] = override_get_db  # type: ignore


@pytest_asyncio.fixture
async def db_session():
    """AsyncSession, полностью изолированная save‑point‑ом."""
    async with engine.connect() as conn:  # type: AsyncConnection
        # начало “внешней” транзакции
        trans = await conn.begin()
        session: AsyncSession = AsyncSession(bind=conn, expire_on_commit=False)

        # после каждого commit() открываем новый save‑point
        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(sess, trans_) -> None:
            if trans_.nested and not trans_._parent.nested:
                sess.begin_nested()

        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()  # откатываем ВСЁ


@pytest_asyncio.fixture
async def client():
    """HTTP-клиент для интеграционных тестов, использующий FastAPI приложение."""
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(db_session, client):
    email_prefix = "testuser_" + uuid.uuid4().hex[:6]
    password = "testpass"
    email = f"{email_prefix}@example.com"

    # Создаем пользователя напрямую
    hashed_password = pwd_context.hash(password)
    user = User(email=email, password=hashed_password)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Генерируем JWT-токен
    token = auth_service.create_access_token({"sub": str(user.id), "email": user.email})
    return {"Authorization": f"Bearer {token}"}
