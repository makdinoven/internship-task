import pytest
from sqlalchemy import select

from app.exceptions.exceptions import (BadRequestDataException,
                                       UserAlreadyActiveException,
                                       UserAlreadyBlockedException,
                                       UserAlreadyExistsException,
                                       UserNotExistsException)
from app.models.db_models import User
from app.schemas.enums import UserStatusEnum
from app.schemas.user_schemas import (RequestUserModel, RequestUserUpdateModel,
                                      UserModel)
from app.services import user_service
from app.services.auth_service import pwd_context


@pytest.mark.asyncio
async def test_create_user_success(db_session):
    """
    Тест успешного создания нового пользователя.
    Проверяем, что пароль хэшируется, а user_service возвращает объект User.
    """
    email = "user1@example.com"
    password = "secret123"

    new_user = await user_service.create_user(user=RequestUserModel(email=email, password=password), session=db_session)

    # Проверяем, что вернулся объект пользователя
    assert isinstance(new_user, User)
    assert new_user.email == email
    # Убеждаемся, что в БД хранится не исходный пароль (он хэширован)
    assert new_user.password != password
    # Проверяем, что хэш правильно сверяется
    assert pwd_context.verify(password, new_user.password)


@pytest.mark.asyncio
async def test_get_user_by_id_found(db_session):
    """
    Тест получения пользователя по ID, когда пользователь существует.
    """
    email = "user2@example.com"
    password = "pass"

    # Сначала создаём пользователя
    user = await user_service.create_user(user=RequestUserModel(email=email, password=password), session=db_session)
    user_id = user.id

    # Получаем пользователя по ID
    found_user = await user_service.get_user_by_id(db_session, user_id)
    assert found_user is not None
    assert found_user.email == email
    assert found_user.id == user_id


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db_session):
    """
    Тест попытки получить пользователя по несуществующему ID.
    Ожидаем UserNotExistsException.
    """
    non_existent_id = 99999

    with pytest.raises(UserNotExistsException) as exc_info:
        await user_service.get_user_by_id(db_session, non_existent_id)

    # Можно проверить, что в тексте исключения есть ID
    assert str(non_existent_id) in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_user_duplicate_email(db_session):
    """
    Тест, что при создании пользователя с дублирующимся email исключение UserAlreadyExistsException.
    """
    email = "dup@example.com"
    password = "password"

    # Создаём первого пользователя
    await user_service.create_user(user=RequestUserModel(email=email, password=password), session=db_session)

    # Попытка создать второго пользователя с тем же email
    with pytest.raises(UserAlreadyExistsException) as exc_info:
        await user_service.create_user(user=RequestUserModel(email=email, password=password), session=db_session)

    # Убеждаемся, что в тексте ошибки упоминается email
    assert f"User {email} already exists." in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_user_status_success_active_to_blocked(db_session):
    """
    Тест успешного обновления статуса пользователя с ACTIVE на BLOCKED.
    Проверяем корректное изменение статуса и возврат обновленных данных.
    """
    # Создаем тестового пользователя
    test_user = await user_service.create_user(
        user=RequestUserModel(email="status_test@example.com", password="password"), session=db_session
    )

    # Меняем статус на BLOCKED
    updated_user = await user_service.update_user_status(
        user_id=test_user.id, status_update=RequestUserUpdateModel(status=UserStatusEnum.BLOCKED), session=db_session
    )

    # Проверяем возвращаемые данные
    assert isinstance(updated_user, UserModel)
    assert updated_user.status == UserStatusEnum.BLOCKED

    # Проверяем фактическое изменение в БД
    db_user = (await db_session.execute(select(User).where(User.id == test_user.id))).scalar()
    assert db_user.status == UserStatusEnum.BLOCKED


@pytest.mark.asyncio
async def test_update_user_status_success_blocked_to_active(db_session):
    """
    Тест успешного обновления статуса пользователя с BLOCKED обратно на ACTIVE.
    """
    # Создаем и блокируем пользователя
    test_user = await user_service.create_user(
        user=RequestUserModel(email="blocked_user@example.com", password="password"), session=db_session
    )
    await user_service.update_user_status(
        user_id=test_user.id, status_update=RequestUserUpdateModel(status=UserStatusEnum.BLOCKED), session=db_session
    )

    # Возвращаем статус ACTIVE
    updated_user = await user_service.update_user_status(
        user_id=test_user.id, status_update=RequestUserUpdateModel(status=UserStatusEnum.ACTIVE), session=db_session
    )

    assert updated_user.status == UserStatusEnum.ACTIVE
    db_user = (await db_session.execute(select(User).where(User.id == test_user.id))).scalar()
    assert db_user.status == UserStatusEnum.ACTIVE


@pytest.mark.asyncio
async def test_update_user_status_same_status_active(db_session):
    """
    Тест попытки обновить статус на тот же ACTIVE.
    Должно вызывать UserAlreadyActiveException.
    """
    test_user = await user_service.create_user(
        user=RequestUserModel(email="active_user@example.com", password="password"), session=db_session
    )

    with pytest.raises(UserAlreadyActiveException) as exc_info:
        await user_service.update_user_status(
            user_id=test_user.id, status_update=RequestUserUpdateModel(status=UserStatusEnum.ACTIVE), session=db_session
        )

    assert str(test_user.id) in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_user_status_same_status_blocked(db_session):
    """
    Тест попытки обновить статус на тот же BLOCKED.
    Должно вызывать UserAlreadyBlockedException.
    """
    test_user = await user_service.create_user(
        user=RequestUserModel(email="blocked_test@example.com", password="password"), session=db_session
    )
    await user_service.update_user_status(
        user_id=test_user.id, status_update=RequestUserUpdateModel(status=UserStatusEnum.BLOCKED), session=db_session
    )

    with pytest.raises(UserAlreadyBlockedException) as exc_info:
        await user_service.update_user_status(
            user_id=test_user.id,
            status_update=RequestUserUpdateModel(status=UserStatusEnum.BLOCKED),
            session=db_session,
        )

    assert str(test_user.id) in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_user_status_not_found(db_session):
    """
    Тест попытки обновить статус несуществующего пользователя.
    Должно вызывать UserNotExistsException.
    """
    non_existent_id = 99999

    with pytest.raises(UserNotExistsException) as exc_info:
        await user_service.update_user_status(
            user_id=non_existent_id,
            status_update=RequestUserUpdateModel(status=UserStatusEnum.BLOCKED),
            session=db_session,
        )

    assert str(non_existent_id) in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_user_status_invalid_id(db_session):
    """
    Тест попытки обновить статус с некорректным ID пользователя.
    Должно вызывать BadRequestDataException.
    """
    with pytest.raises(BadRequestDataException) as exc_info:
        await user_service.update_user_status(
            user_id=-1, status_update=RequestUserUpdateModel(status=UserStatusEnum.BLOCKED), session=db_session
        )

    assert "Invalid user ID" in str(exc_info.value)
