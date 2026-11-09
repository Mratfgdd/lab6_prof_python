import math

from student_app.exceptions import EmptyGradesError, InvalidGradeError

MIN_GRADE = 0.0
MAX_GRADE = 100.0
LEVELS = ("excellent", "good", "satisfactory", "unsatisfactory")


def validate_grade(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidGradeError(f"оцінка має бути числом, отримано {value!r}")
    grade = float(value)
    if math.isnan(grade) or not MIN_GRADE <= grade <= MAX_GRADE:
        raise InvalidGradeError(f"оцінка {value!r} поза діапазоном {MIN_GRADE:g}–{MAX_GRADE:g}")
    return grade


def average_of(grades: tuple[float, ...] | list[float]) -> float:
    if not grades:
        raise EmptyGradesError("неможливо обчислити середній бал без оцінок")
    return sum(grades) / len(grades)


def classify_grade(average: float) -> str:
    value = validate_grade(average)
    if value >= 90:
        return "excellent"
    if value >= 75:
        return "good"
    if value >= 60:
        return "satisfactory"
    return "unsatisfactory"
