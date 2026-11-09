import re
from dataclasses import dataclass, replace

from student_app.exceptions import InvalidStudentError
from student_app.grading import average_of, classify_grade, validate_grade

GROUP_PATTERN = re.compile(r"[A-Z]{2}-[0-9]{2}")


def normalize_group(group: str) -> str:
    return group.strip().upper()


@dataclass(frozen=True)
class Student:
    student_id: int
    first_name: str
    last_name: str
    group: str
    grades: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.student_id, bool) or not isinstance(self.student_id, int):
            raise InvalidStudentError("student_id має бути цілим числом")
        if self.student_id <= 0:
            raise InvalidStudentError("student_id має бути додатним")
        for field_name in ("first_name", "last_name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidStudentError(f"поле {field_name} є обов'язковим")
        object.__setattr__(self, "first_name", self.first_name.strip())
        object.__setattr__(self, "last_name", self.last_name.strip())
        if not isinstance(self.group, str) or not GROUP_PATTERN.fullmatch(
            normalize_group(self.group)
        ):
            raise InvalidStudentError(f"некоректна група {self.group!r}, очікується формат PI-21")
        if not isinstance(self.grades, tuple | list):
            raise InvalidStudentError("grades має бути послідовністю оцінок")
        object.__setattr__(self, "group", normalize_group(self.group))
        object.__setattr__(self, "grades", tuple(validate_grade(grade) for grade in self.grades))

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"

    @property
    def average(self) -> float:
        return average_of(self.grades)

    @property
    def level(self) -> str:
        return classify_grade(self.average)

    def with_grade(self, grade: float) -> "Student":
        return replace(self, grades=(*self.grades, validate_grade(grade)))
