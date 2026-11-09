import os

import pytest

from student_app import models
from student_app.models import Student


@pytest.fixture(autouse=True)
def mutant(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.environ.get("STUDENT_MUTANT") == "1":
        monkeypatch.setattr(models, "average_of", lambda grades: max(grades))


def make_student() -> Student:
    return Student(1, "Олена", "Коваленко", "PI-21", (60.0, 80.0, 100.0))


def test_average_weak() -> None:
    _ = make_student().average


def test_average_strong() -> None:
    assert make_student().average == pytest.approx(80.0)
