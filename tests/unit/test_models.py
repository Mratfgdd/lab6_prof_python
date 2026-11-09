from dataclasses import FrozenInstanceError

import pytest
from conftest import StudentFactory

from student_app.exceptions import EmptyGradesError, InvalidGradeError, InvalidStudentError
from student_app.models import Student


def test_student_is_created_with_normalized_fields() -> None:
    student = Student(7, "  Олена ", " Коваленко", " pi-21 ", (90, 85.5))
    assert student.first_name == "Олена"
    assert student.last_name == "Коваленко"
    assert student.group == "PI-21"
    assert student.grades == (90.0, 85.5)
    assert student.full_name == "Коваленко Олена"


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
def test_student_rejects_invalid_required_fields(fields: dict[str, object], message: str) -> None:
    valid = {"student_id": 1, "first_name": "Олена", "last_name": "Коваленко", "group": "PI-21"}
    with pytest.raises(InvalidStudentError, match=message):
        Student(**(valid | fields))


def test_student_rejects_invalid_grade_inside_collection() -> None:
    with pytest.raises(InvalidGradeError):
        Student(1, "Олена", "Коваленко", "PI-21", (90, 101))


@pytest.mark.parametrize("grades", [None, "90", 90], ids=["none", "text", "number"])
def test_student_rejects_grades_that_are_not_a_sequence(grades: object) -> None:
    with pytest.raises(InvalidStudentError, match="grades"):
        Student(1, "Олена", "Коваленко", "PI-21", grades)


def test_student_is_immutable(student_factory: StudentFactory) -> None:
    student = student_factory()
    with pytest.raises(FrozenInstanceError):
        student.group = "PI-22"


def test_average_is_arithmetic_mean_of_grades(student_factory: StudentFactory) -> None:
    student = student_factory(grades=(88.5, 92.25, 79.0))
    assert student.average == pytest.approx(86.58333333)


def test_average_tolerates_floating_point_noise(student_factory: StudentFactory) -> None:
    student = student_factory(grades=(0.1, 0.2))
    assert student.average != 0.15
    assert student.average == pytest.approx(0.15)


def test_average_of_single_grade_is_that_grade(student_factory: StudentFactory) -> None:
    assert student_factory(grades=(73.0,)).average == 73.0


def test_average_without_grades_raises_custom_error(student_factory: StudentFactory) -> None:
    student = student_factory(grades=())
    with pytest.raises(EmptyGradesError, match="без оцінок") as error:
        _ = student.average
    assert isinstance(error.value, ValueError)


def test_with_grade_returns_new_student_and_keeps_original(student_factory: StudentFactory) -> None:
    original = student_factory(grades=(80.0,))
    updated = original.with_grade(100)
    assert original.grades == (80.0,)
    assert updated.grades == (80.0, 100.0)
    assert updated.average == pytest.approx(90.0)


def test_with_invalid_grade_raises_and_keeps_original(student_factory: StudentFactory) -> None:
    original = student_factory(grades=(80.0,))
    with pytest.raises(InvalidGradeError):
        original.with_grade(100.01)
    assert original.grades == (80.0,)


def test_student_level_follows_average(student_factory: StudentFactory) -> None:
    assert student_factory(grades=(95.0, 91.0)).level == "excellent"
    assert student_factory(grades=(50.0,)).level == "unsatisfactory"
