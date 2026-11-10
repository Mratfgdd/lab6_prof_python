"""Модель студента та шкала рівнів успішності."""

from dataclasses import dataclass, replace

from student_manager.validators import (
    validate_average_grade,
    validate_group,
    validate_name,
    validate_student_id,
)

LEVELS = ("excellent", "good", "satisfactory", "unsatisfactory")


def classify_grade(average_grade: float) -> str:
    """Повертає рівень успішності за середнім балом від 0 до 100."""
    value = validate_average_grade(average_grade)
    if value >= 90:
        return "excellent"
    if value >= 75:
        return "good"
    if value >= 60:
        return "satisfactory"
    return "unsatisfactory"


@dataclass(frozen=True)
class Student:
    """Студент: ідентифікатор, ім'я, група й середній бал за шкалою 0-100."""

    student_id: int
    first_name: str
    last_name: str
    group: str
    average_grade: float

    def __post_init__(self) -> None:
        """Перевіряє поля та зберігає їх у нормалізованому вигляді."""
        values = {
            "student_id": validate_student_id(self.student_id),
            "first_name": validate_name(self.first_name, "first_name"),
            "last_name": validate_name(self.last_name, "last_name"),
            "group": validate_group(self.group),
            "average_grade": validate_average_grade(self.average_grade),
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def full_name(self) -> str:
        """Ім'я та прізвище через пробіл."""
        return f"{self.first_name} {self.last_name}"

    @property
    def level(self) -> str:
        """Рівень успішності за середнім балом."""
        return classify_grade(self.average_grade)

    def with_average_grade(self, average_grade: float) -> "Student":
        """Повертає копію студента з новим середнім балом."""
        return replace(self, average_grade=average_grade)
