"""Валідатори: межі середнього бала, формат групи, ідентифікатор, ім'я."""

import math
from typing import Any

import pytest

from student_manager.exceptions import InvalidGradeError, InvalidStudentError
from student_manager.validators import (
    normalize_group,
    parse_average_grade,
    parse_student_id,
    validate_average_grade,
    validate_group,
    validate_name,
    validate_student_id,
)


@pytest.mark.parametrize(
    "value",
    [0, 0.01, 50, 99.99, 100, 100.0],
    ids=[
        "min",
        "just-above-min",
        "middle",
        "just-below-max",
        "max",
        "max-float",
    ],
)
def test_valid_average_grade_is_accepted(value: float) -> None:
    assert validate_average_grade(value) == pytest.approx(float(value))


@pytest.mark.parametrize(
    "value",
    [
        -0.01,
        -1,
        100.01,
        101,
        1000,
        math.nan,
        math.inf,
        -math.inf,
        "90",
        None,
        True,
        [90],
    ],
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
def test_invalid_average_grade_raises_validation_error(value: Any) -> None:
    with pytest.raises(InvalidGradeError):
        validate_average_grade(value)


def test_invalid_grade_error_names_field_and_offending_value() -> None:
    with pytest.raises(InvalidGradeError, match="101") as error:
        validate_average_grade(101)
    assert error.value.field == "average_grade"
    assert isinstance(error.value, ValueError)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("90", 90.0),
        (" 75.5 ", 75.5),
        ("0", 0.0),
        ("100", 100.0),
        ("99.99", 99.99),
    ],
    ids=["integer", "spaces", "zero", "maximum", "fraction"],
)
def test_parse_average_grade_converts_text(text: str, expected: float) -> None:
    assert parse_average_grade(text) == pytest.approx(expected)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "abc",
        "9o",
        "nan",
        "inf",
        "101",
        "-1",
        "-0",
        "+90",
        "90,5",
        "1e2",
        "9_0",
        "٩٠",
        ".5",
        "5.",
    ],
    ids=repr,
)
def test_parse_average_grade_rejects_everything_but_plain_decimals(
    text: str,
) -> None:
    with pytest.raises(InvalidGradeError):
        parse_average_grade(text)


def test_negative_zero_is_stored_as_positive_zero() -> None:
    assert math.copysign(1.0, validate_average_grade(-0.0)) == 1.0


def test_parse_average_grade_error_names_field_and_offending_text() -> None:
    with pytest.raises(InvalidGradeError, match="incorrect") as error:
        parse_average_grade("incorrect")
    assert error.value.field == "average_grade"


@pytest.mark.parametrize("value", [1, 42, 10**9])
def test_valid_student_id_is_returned(value: int) -> None:
    assert validate_student_id(value) == value


@pytest.mark.parametrize(
    "value", [0, -1, True, False, "1", 1.0, None], ids=repr
)
def test_invalid_student_id_raises_validation_error(value: Any) -> None:
    with pytest.raises(InvalidStudentError) as error:
        validate_student_id(value)
    assert error.value.field == "student_id"


@pytest.mark.parametrize(
    ("text", "expected"), [("1", 1), (" 42 ", 42), ("007", 7)]
)
def test_parse_student_id_accepts_ascii_digits(
    text: str, expected: int
) -> None:
    assert parse_student_id(text) == expected


@pytest.mark.parametrize(
    "text", ["", "abc", "4.5", "-3", "+3", "0", "١٢", "²"], ids=repr
)
def test_parse_student_id_rejects_everything_but_positive_integers(
    text: str,
) -> None:
    with pytest.raises(InvalidStudentError):
        parse_student_id(text)


def test_name_is_stripped() -> None:
    assert validate_name("  Олена ", "first_name") == "Олена"


@pytest.mark.parametrize("value", ["", "   ", None, 5], ids=repr)
def test_empty_or_non_text_name_is_rejected(value: Any) -> None:
    with pytest.raises(InvalidStudentError, match="last_name") as error:
        validate_name(value, "last_name")
    assert error.value.field == "last_name"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PI-21", "PI-21"),
        ("pi-21", "PI-21"),
        (" PI-22 ", "PI-22"),
        ("феп-31", "ФЕП-31"),
    ],
    ids=["canonical", "lowercase", "spaces", "cyrillic"],
)
def test_valid_group_is_normalized(raw: str, expected: str) -> None:
    assert validate_group(raw) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "PI21",
        "21-PI",
        "P-21",
        "ABCDEF-21",
        "PI-2",
        "PI-211",
        "PI-٢١",
        None,
        21,
    ],
    ids=repr,
)
def test_invalid_group_is_rejected(value: Any) -> None:
    with pytest.raises(InvalidStudentError) as error:
        validate_group(value)
    assert error.value.field == "group"


def test_normalize_group_strips_and_uppercases() -> None:
    assert normalize_group("  pi-23\t") == "PI-23"
