"""Student: створення, обов'язкові поля, незмінність, рівні успішності."""

from dataclasses import FrozenInstanceError
from typing import Any

import pytest
from support import StudentFactory

from student_manager.exceptions import InvalidGradeError, InvalidStudentError
from student_manager.models import LEVELS, Student, classify_grade


def test_student_is_created_with_normalized_fields() -> None:
    student = Student(7, "  Олена ", " Коваленко", " pi-21 ", 85)
    assert student.student_id == 7
    assert student.first_name == "Олена"
    assert student.last_name == "Коваленко"
    assert student.group == "PI-21"
    assert student.average_grade == pytest.approx(85.0)
    assert student.full_name == "Олена Коваленко"


def test_integer_average_grade_is_stored_as_float() -> None:
    assert isinstance(
        Student(1, "Олена", "Коваленко", "PI-21", 85).average_grade, float
    )


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"student_id": 0}, "додатним"),
        ({"student_id": -5}, "додатним"),
        ({"student_id": True}, "цілим"),
        ({"student_id": "1"}, "цілим"),
        ({"first_name": ""}, "first_name"),
        ({"first_name": "   "}, "first_name"),
        ({"last_name": ""}, "last_name"),
        ({"last_name": None}, "last_name"),
        ({"group": ""}, "група"),
        ({"group": "PI21"}, "група"),
        ({"group": "21-PI"}, "група"),
        ({"group": None}, "група"),
        ({"group": 21}, "група"),
        ({"group": "PI-٢١"}, "група"),
    ],
    ids=[
        "id-zero",
        "id-negative",
        "id-bool",
        "id-text",
        "first-name-empty",
        "first-name-blank",
        "last-name-empty",
        "last-name-none",
        "group-empty",
        "group-no-dash",
        "group-reversed",
        "group-none",
        "group-number",
        "group-unicode-digits",
    ],
)
def test_student_rejects_invalid_required_fields(
    fields: dict[str, Any], message: str
) -> None:
    valid: dict[str, Any] = {
        "student_id": 1,
        "first_name": "Олена",
        "last_name": "Коваленко",
        "group": "PI-21",
        "average_grade": 90.0,
    }
    with pytest.raises(InvalidStudentError, match=message):
        Student(**(valid | fields))


@pytest.mark.parametrize(
    "grade",
    [-0.01, 100.01, float("nan"), "90", None, True],
    ids=["below-min", "above-max", "nan", "text", "none", "bool"],
)
def test_student_rejects_invalid_average_grade(grade: Any) -> None:
    with pytest.raises(InvalidGradeError) as error:
        Student(1, "Олена", "Коваленко", "PI-21", grade)
    assert error.value.field == "average_grade"


@pytest.mark.parametrize(
    "grade",
    [0, 0.01, 50, 99.99, 100],
    ids=["min", "just-above-min", "middle", "just-below-max", "max"],
)
def test_student_accepts_boundary_average_grades(grade: float) -> None:
    student = Student(1, "Олена", "Коваленко", "PI-21", grade)
    assert student.average_grade == pytest.approx(float(grade))


def test_student_is_immutable(student_factory: StudentFactory) -> None:
    student: Any = student_factory()
    with pytest.raises(FrozenInstanceError):
        student.group = "PI-22"


def test_students_with_same_fields_are_equal(
    student_factory: StudentFactory,
) -> None:
    first = student_factory(student_id=1)
    second = student_factory(student_id=1)
    assert first == second
    assert first is not second


def test_with_average_grade_returns_new_student_and_keeps_original(
    student_factory: StudentFactory,
) -> None:
    original = student_factory(average_grade=80.0)
    updated = original.with_average_grade(95.5)
    assert original.average_grade == pytest.approx(80.0)
    assert updated.average_grade == pytest.approx(95.5)
    assert updated.student_id == original.student_id


def test_with_invalid_average_grade_raises_and_keeps_original(
    student_factory: StudentFactory,
) -> None:
    original = student_factory(average_grade=80.0)
    with pytest.raises(InvalidGradeError):
        original.with_average_grade(100.01)
    assert original.average_grade == pytest.approx(80.0)


@pytest.mark.parametrize(
    ("average", "level"),
    [
        (0, "unsatisfactory"),
        (59.99, "unsatisfactory"),
        (60, "satisfactory"),
        (74.99, "satisfactory"),
        (75, "good"),
        (89.99, "good"),
        (90, "excellent"),
        (100, "excellent"),
    ],
    ids=[
        "min",
        "below-60",
        "exactly-60",
        "below-75",
        "exactly-75",
        "below-90",
        "exactly-90",
        "max",
    ],
)
def test_classify_grade_boundaries(average: float, level: str) -> None:
    assert classify_grade(average) == level
    assert level in LEVELS


@pytest.mark.parametrize("average", [-0.01, 100.01])
def test_classify_grade_rejects_values_outside_scale(average: float) -> None:
    with pytest.raises(InvalidGradeError):
        classify_grade(average)


def test_student_level_follows_average_grade(
    student_factory: StudentFactory,
) -> None:
    assert student_factory(average_grade=93.0).level == "excellent"
    assert student_factory(average_grade=50.0).level == "unsatisfactory"
