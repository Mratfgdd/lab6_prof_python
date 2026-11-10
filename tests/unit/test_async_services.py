"""AsyncStudentService: AsyncMock-репозиторій, awaited-перевірки, збої."""

from unittest.mock import AsyncMock

import pytest
from support import StudentFactory

from student_manager.exceptions import (
    NoStudentsError,
    RepositoryError,
    StudentNotFoundError,
)
from student_manager.repositories import AsyncStudentRepository
from student_manager.services import AsyncStudentService


@pytest.fixture
def async_repository() -> AsyncMock:
    """AsyncMock за інтерфейсом AsyncStudentRepository."""
    return AsyncMock(spec=AsyncStudentRepository)


@pytest.fixture
def async_service(async_repository: AsyncMock) -> AsyncStudentService:
    """Сервіс з підміненим асинхронним сховищем."""
    return AsyncStudentService(async_repository)


@pytest.mark.asyncio
async def test_load_returns_student_from_async_repository(
    async_service: AsyncStudentService,
    async_repository: AsyncMock,
    student_factory: StudentFactory,
) -> None:
    student = student_factory(student_id=1)
    async_repository.get.return_value = student
    assert await async_service.load(1) is student
    async_repository.get.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_load_of_missing_student_raises_not_found(
    async_service: AsyncStudentService, async_repository: AsyncMock
) -> None:
    async_repository.get.return_value = None
    with pytest.raises(StudentNotFoundError, match="42"):
        await async_service.load(42)
    async_repository.get.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_connection_failure_becomes_repository_error_with_cause(
    async_service: AsyncStudentService, async_repository: AsyncMock
) -> None:
    async_repository.get.side_effect = ConnectionError("таймаут")
    with pytest.raises(RepositoryError, match="сховище недоступне") as error:
        await async_service.load(1)
    assert isinstance(error.value.__cause__, ConnectionError)


@pytest.mark.asyncio
async def test_load_many_awaits_repository_for_every_id(
    async_service: AsyncStudentService,
    async_repository: AsyncMock,
    student_factory: StudentFactory,
) -> None:
    first, second = (
        student_factory(student_id=1),
        student_factory(student_id=2),
    )
    async_repository.get.side_effect = [first, second]
    assert await async_service.load_many([1, 2]) == [first, second]
    assert async_repository.get.await_count == 2


@pytest.mark.asyncio
async def test_load_many_with_missing_student_raises(
    async_service: AsyncStudentService,
    async_repository: AsyncMock,
    student_factory: StudentFactory,
) -> None:
    async_repository.get.side_effect = [student_factory(student_id=1), None]
    with pytest.raises(StudentNotFoundError):
        await async_service.load_many([1, 2])


@pytest.mark.asyncio
async def test_load_many_of_empty_list_does_not_touch_repository(
    async_service: AsyncStudentService, async_repository: AsyncMock
) -> None:
    assert await async_service.load_many([]) == []
    async_repository.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_best_student_uses_all_students_from_repository(
    async_service: AsyncStudentService,
    async_repository: AsyncMock,
    student_factory: StudentFactory,
) -> None:
    weak = student_factory(student_id=1, average_grade=60.0)
    strong = student_factory(student_id=2, average_grade=96.0)
    async_repository.all.return_value = [weak, strong]
    assert await async_service.best_student() is strong
    async_repository.all.assert_awaited_once_with()
    async_repository.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_best_student_of_empty_repository_raises(
    async_service: AsyncStudentService, async_repository: AsyncMock
) -> None:
    async_repository.all.return_value = []
    with pytest.raises(NoStudentsError):
        await async_service.best_student()


@pytest.mark.asyncio
async def test_best_student_wraps_connection_failure(
    async_service: AsyncStudentService, async_repository: AsyncMock
) -> None:
    async_repository.all.side_effect = ConnectionError("розрив з'єднання")
    with pytest.raises(RepositoryError):
        await async_service.best_student()
