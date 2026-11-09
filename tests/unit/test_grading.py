import math

import pytest

from student_app.exceptions import EmptyGradesError, InvalidGradeError
from student_app.grading import LEVELS, average_of, classify_grade, validate_grade


@pytest.mark.parametrize(
    "value",
    [0, 0.01, 50, 99.99, 100, 100.0],
    ids=["min", "just-above-min", "middle", "just-below-max", "max", "max-float"],
)
def test_validate_grade_accepts_values_inside_range(value: float) -> None:
    assert validate_grade(value) == pytest.approx(float(value))


@pytest.mark.parametrize(
    "value",
    [-0.01, -1, 100.01, 101, 1000, math.nan, math.inf, -math.inf, "90", None, True, [90]],
    ids=[
        "below-min",
        "negative",
        "just-above-max",
        "above-max",
        "huge",
        "nan",
        "inf",
        "minus-inf",
        "text",
        "none",
        "bool",
        "list",
    ],
)
def test_validate_grade_rejects_invalid_values(value: object) -> None:
    with pytest.raises(InvalidGradeError):
        validate_grade(value)


def test_validate_grade_message_contains_offending_value() -> None:
    with pytest.raises(InvalidGradeError, match="101"):
        validate_grade(101)


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


def test_average_of_list_and_tuple() -> None:
    assert average_of([80.0, 90.0, 100.0]) == pytest.approx(90.0)
    assert average_of((70.5, 71.5)) == pytest.approx(71.0)


def test_average_of_empty_collection_raises() -> None:
    with pytest.raises(EmptyGradesError):
        average_of([])
