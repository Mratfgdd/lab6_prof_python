"""Перевірка й нормалізація даних студента."""

import math
import re

from student_manager.exceptions import InvalidGradeError, InvalidStudentError

MIN_GRADE = 0.0
MAX_GRADE = 100.0
GROUP_PATTERN = re.compile(r"[A-ZА-ЯІЇЄҐ]{2,5}-[0-9]{2}")
GRADE_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def validate_student_id(value: object) -> int:
    """Повертає додатний цілий ідентифікатор; bool числом не вважається."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidStudentError(
            f"student_id має бути цілим числом, отримано {value!r}",
            field="student_id",
        )
    if value <= 0:
        raise InvalidStudentError(
            f"student_id має бути додатним, отримано {value}",
            field="student_id",
        )
    return value


def parse_student_id(text: str) -> int:
    """Перетворює текст на ідентифікатор; приймає лише цифри 0-9."""
    candidate = text.strip()
    if not (candidate.isascii() and candidate.isdigit()):
        raise InvalidStudentError(
            f"student_id має бути цілим числом, отримано {text!r}",
            field="student_id",
        )
    return validate_student_id(int(candidate))


def validate_name(value: object, field: str) -> str:
    """Повертає ім'я без крайніх пробілів; порожній рядок недопустимий."""
    if not isinstance(value, str) or not value.strip():
        raise InvalidStudentError(f"поле {field} є обов'язковим", field=field)
    return value.strip()


def normalize_group(group: str) -> str:
    """Приводить код групи до верхнього регістру без пробілів."""
    return group.strip().upper()


def validate_group(value: object) -> str:
    """Повертає код групи у форматі PI-21 або піднімає InvalidStudentError."""
    if not isinstance(value, str) or not GROUP_PATTERN.fullmatch(
        normalize_group(value)
    ):
        raise InvalidStudentError(
            f"некоректна група {value!r}, очікується формат PI-21",
            field="group",
        )
    return normalize_group(value)


def validate_average_grade(value: object) -> float:
    """Повертає середній бал як float, якщо він у межах від 0 до 100."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidGradeError(
            f"середній бал має бути числом, отримано {value!r}"
        )
    grade = float(value)
    if math.isnan(grade) or not MIN_GRADE <= grade <= MAX_GRADE:
        raise InvalidGradeError(
            f"середній бал {value!r} поза діапазоном "
            f"{MIN_GRADE:g}–{MAX_GRADE:g}"
        )
    return grade + 0.0


def parse_average_grade(text: str) -> float:
    """Перетворює десятковий запис (90 або 87.5) на середній бал."""
    candidate = text.strip()
    if not GRADE_PATTERN.fullmatch(candidate):
        raise InvalidGradeError(
            f"середній бал {text!r} має бути десятковим числом, наприклад 87.5"
        )
    return validate_average_grade(float(candidate))
