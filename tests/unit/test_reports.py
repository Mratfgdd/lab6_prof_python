"""Звіт: порожня колекція, групи, найкращий студент, ризик, округлення."""

import pytest
from support import StudentFactory

from student_manager.reports import build_report, rounded


def test_report_of_empty_collection_has_zero_counts_and_no_best_student() -> (
    None
):
    report = build_report([], pass_threshold=60.0)
    assert report == {
        "total_students": 0,
        "average_grade": None,
        "best_student": None,
        "groups": [],
        "levels": {
            "excellent": 0,
            "good": 0,
            "satisfactory": 0,
            "unsatisfactory": 0,
        },
        "at_risk": [],
    }


def test_report_summarizes_groups_and_best_student(
    student_factory: StudentFactory,
) -> None:
    students = [
        student_factory("Бондар", "Ірина", "PI-22", 99.5, 3),
        student_factory("Коваленко", "Олена", "PI-21", 95.0, 1),
        student_factory("Мельник", "Андрій", "PI-21", 78.0, 2),
    ]
    report = build_report(students, pass_threshold=60.0)
    assert report["total_students"] == 3
    assert report["average_grade"] == pytest.approx(90.83, abs=0.005)
    assert report["best_student"] == {
        "student_id": 3,
        "name": "Ірина Бондар",
        "group": "PI-22",
        "average_grade": 99.5,
    }
    assert report["groups"] == [
        {"group": "PI-21", "students": 2, "average_grade": 86.5},
        {"group": "PI-22", "students": 1, "average_grade": 99.5},
    ]


@pytest.mark.parametrize(
    ("average_grade", "at_risk"),
    [(59.99, [1]), (60.0, []), (0.0, [1]), (100.0, [])],
    ids=["just-below", "exactly-threshold", "minimum", "maximum"],
)
def test_at_risk_students_are_below_threshold(
    student_factory: StudentFactory, average_grade: float, at_risk: list[int]
) -> None:
    student = student_factory(average_grade=average_grade, student_id=1)
    report = build_report([student], pass_threshold=60.0)
    assert report["at_risk"] == at_risk


def test_report_counts_students_by_level(
    student_factory: StudentFactory,
) -> None:
    students = [student_factory(average_grade=g) for g in (95, 80, 65, 10, 91)]
    levels = build_report(students, pass_threshold=60.0)["levels"]
    assert levels == {
        "excellent": 2,
        "good": 1,
        "satisfactory": 1,
        "unsatisfactory": 1,
    }


@pytest.mark.parametrize(
    ("value", "expected"), [(None, None), (2.346, 2.35), (2.0, 2.0)]
)
def test_rounded_keeps_none_and_rounds_to_hundredths(
    value: float | None, expected: float | None
) -> None:
    assert rounded(value) == expected
