"""Експеримент 1-2: слабкий тест лише виконує код, сильний - перевіряє."""

import os

import pytest

from student_manager import services
from student_manager.models import Student


@pytest.fixture(autouse=True)
def mutant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Підміняє середнє на максимум лише за змінної STUDENT_MUTANT=1."""
    if os.environ.get("STUDENT_MUTANT") == "1":
        monkeypatch.setattr(
            services,
            "calculate_group_average",
            lambda students: max(s.average_grade for s in students),
        )


def make_students() -> list[Student]:
    """Три студенти із середнім балом групи 80."""
    return [
        Student(1, "Олена", "Коваленко", "PI-21", 60.0),
        Student(2, "Андрій", "Мельник", "PI-21", 80.0),
        Student(3, "Ірина", "Бондар", "PI-21", 100.0),
    ]


def test_average_weak() -> None:
    services.calculate_group_average(make_students())


def test_average_strong() -> None:
    average = services.calculate_group_average(make_students())
    assert average == pytest.approx(80.0)
