import os
from unittest.mock import create_autospec

import pytest

from student_app.exceptions import StudentNotFoundError
from student_app.models import Student
from student_app.repositories import InMemoryStudentRepository, StudentRepository
from student_app.services import Notifier, StudentService


def refactored_get(self: StudentService, student_id: int) -> Student:
    for student in self._repository.all():
        if student.student_id == student_id:
            return student
    raise StudentNotFoundError(f"студента {student_id} не знайдено")


@pytest.fixture(autouse=True)
def refactoring(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.environ.get("STUDENT_REFACTORED") == "1":
        monkeypatch.setattr(StudentService, "get", refactored_get)


def test_get_with_mock_repository() -> None:
    student = Student(7, "Олена", "Коваленко", "PI-21", (90.0,))
    repository = create_autospec(StudentRepository, instance=True)
    repository.get.return_value = student
    repository.all.return_value = [student]
    service = StudentService(repository, create_autospec(Notifier, instance=True))
    assert service.get(7) is student
    repository.get.assert_called_once_with(7)


def test_get_with_fake_repository() -> None:
    student = Student(7, "Олена", "Коваленко", "PI-21", (90.0,))
    repository = InMemoryStudentRepository()
    repository.add(student)
    service = StudentService(repository, create_autospec(Notifier, instance=True))
    assert service.get(7) is student
