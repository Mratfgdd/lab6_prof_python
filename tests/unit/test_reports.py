import pytest
from conftest import StudentFactory

from student_app.exceptions import NoStudentsError
from student_app.reports import average_or_none, best_of, build_report, level_counts, rounded


def test_report_of_empty_collection_has_zero_counts_and_no_best_student() -> None:
    report = build_report([], pass_threshold=60.0)
    assert report == {
        "total_students": 0,
        "graded_students": 0,
        "average_grade": None,
        "best_student": None,
        "groups": [],
        "levels": {"excellent": 0, "good": 0, "satisfactory": 0, "unsatisfactory": 0},
        "at_risk": [],
    }


def test_report_summarizes_groups_and_best_student(student_factory: StudentFactory) -> None:
    students = [
        student_factory("Бондар", group="PI-22", grades=(100.0, 99.5), student_id=3),
        student_factory("Коваленко", group="PI-21", grades=(95.0, 92.0, 98.0), student_id=1),
        student_factory("Гнатюк", group="PI-21", grades=(), student_id=5),
    ]
    report = build_report(students, pass_threshold=60.0)
    assert report["total_students"] == 3
    assert report["graded_students"] == 2
    assert report["average_grade"] == pytest.approx(97.38, abs=0.005)
    assert report["best_student"] == {
        "student_id": 3,
        "name": "Бондар Олена",
        "group": "PI-22",
        "average": 99.75,
    }
    assert report["groups"] == [
        {"group": "PI-21", "students": 2, "average": 95.0},
        {"group": "PI-22", "students": 1, "average": 99.75},
    ]


def test_group_without_graded_students_has_no_average(student_factory: StudentFactory) -> None:
    report = build_report([student_factory(grades=())], pass_threshold=60.0)
    assert report["groups"][0]["average"] is None
    assert report["best_student"] is None


@pytest.mark.parametrize(
    ("grades", "at_risk"),
    [((59.99,), [1]), ((60.0,), []), ((0.0,), [1]), ((100.0,), [])],
    ids=["just-below", "exactly-threshold", "minimum", "maximum"],
)
def test_at_risk_students_are_below_threshold(
    student_factory: StudentFactory, grades: tuple[float, ...], at_risk: list[int]
) -> None:
    report = build_report([student_factory(grades=grades, student_id=1)], pass_threshold=60.0)
    assert report["at_risk"] == at_risk


def test_level_counts_covers_every_level(student_factory: StudentFactory) -> None:
    students = [student_factory(grades=(value,)) for value in (95.0, 80.0, 65.0, 10.0, 91.0)]
    assert level_counts(students) == {
        "excellent": 2,
        "good": 1,
        "satisfactory": 1,
        "unsatisfactory": 1,
    }


def test_best_of_without_graded_students_raises(student_factory: StudentFactory) -> None:
    with pytest.raises(NoStudentsError):
        best_of([student_factory(grades=())])


def test_average_or_none_of_empty_collection_is_none() -> None:
    assert average_or_none([]) is None


@pytest.mark.parametrize(("value", "expected"), [(None, None), (2.346, 2.35), (2.0, 2.0)])
def test_rounded_keeps_none_and_rounds_to_hundredths(
    value: float | None, expected: float | None
) -> None:
    assert rounded(value) == expected
