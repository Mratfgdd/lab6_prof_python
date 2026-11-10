"""Сховища студентів: додавання, оновлення, пошук, копії та async-сховище."""

import pytest
from support import StudentFactory

from student_manager.exceptions import (
    DuplicateStudentError,
    StudentNotFoundError,
)
from student_manager.repositories import (
    InMemoryAsyncStudentRepository,
    InMemoryStudentRepository,
)


def test_added_student_can_be_found_by_id(
    repository: InMemoryStudentRepository, student_factory: StudentFactory
) -> None:
    student = student_factory(student_id=11)
    repository.add(student)
    assert repository.get(11) is student


def test_get_of_unknown_id_returns_none(
    repository: InMemoryStudentRepository,
) -> None:
    assert repository.get(404) is None


def test_adding_same_id_twice_is_rejected(
    repository: InMemoryStudentRepository, student_factory: StudentFactory
) -> None:
    repository.add(student_factory(student_id=1, last_name="Перший"))
    with pytest.raises(DuplicateStudentError, match="1"):
        repository.add(student_factory(student_id=1, last_name="Другий"))
    assert [s.last_name for s in repository.all()] == ["Перший"]


def test_update_replaces_stored_student(
    repository: InMemoryStudentRepository, student_factory: StudentFactory
) -> None:
    student = student_factory(student_id=1, average_grade=50.0)
    repository.add(student)
    repository.update(student.with_average_grade(100))
    stored = repository.get(1)
    assert stored is not None
    assert stored.average_grade == pytest.approx(100.0)


def test_update_of_unknown_student_raises(
    repository: InMemoryStudentRepository, student_factory: StudentFactory
) -> None:
    with pytest.raises(StudentNotFoundError):
        repository.update(student_factory(student_id=99))


def test_search_by_last_name_ignores_case_and_spaces(
    repository: InMemoryStudentRepository, student_factory: StudentFactory
) -> None:
    repository.add(student_factory("Мельник", student_id=1))
    repository.add(student_factory("Мельник", "Іван", student_id=2))
    repository.add(student_factory("Бондар", student_id=3))
    found = repository.find_by_last_name("  мЕЛЬНИК ")
    assert sorted(s.student_id for s in found) == [1, 2]


def test_search_by_unknown_last_name_returns_empty_list(
    repository: InMemoryStudentRepository,
) -> None:
    assert repository.find_by_last_name("Ніхто") == []


def test_all_of_empty_repository_is_empty_list(
    repository: InMemoryStudentRepository,
) -> None:
    assert repository.all() == []


def test_all_returns_copy_that_does_not_affect_storage(
    repository: InMemoryStudentRepository, student_factory: StudentFactory
) -> None:
    repository.add(student_factory(student_id=1))
    snapshot = repository.all()
    snapshot.clear()
    assert len(repository.all()) == 1


@pytest.mark.asyncio
async def test_async_repository_returns_students(
    student_factory: StudentFactory,
) -> None:
    student = student_factory(student_id=5)
    repository = InMemoryAsyncStudentRepository([student])
    assert await repository.get(5) is student
    assert await repository.get(6) is None
    assert await repository.all() == [student]


@pytest.mark.asyncio
async def test_empty_async_repository_has_no_students() -> None:
    repository = InMemoryAsyncStudentRepository()
    assert await repository.all() == []
