"""Імпорт студентів із CSV із перевіркою кожного рядка."""

import csv
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from student_manager.exceptions import ImportDataError, ValidationError
from student_manager.models import Student
from student_manager.validators import (
    normalize_group,
    parse_average_grade,
    parse_student_id,
)

REQUIRED_COLUMNS = (
    "student_id",
    "first_name",
    "last_name",
    "group",
    "average_grade",
)


@dataclass(frozen=True)
class ImportIssue:
    """Проблемний рядок файлу: номер рядка й опис помилки."""

    line_number: int
    message: str


@dataclass
class ImportResult:
    """Результат імпорту: прийняті студенти та відхилені рядки."""

    students: list[Student] = field(default_factory=list)
    issues: list[ImportIssue] = field(default_factory=list)


def parse_row(
    row: Mapping[str | None, str | None],
    line_number: int,
    allowed_groups: frozenset[str],
) -> Student:
    """Перетворює рядок CSV на Student або піднімає ImportDataError."""
    if None in row:
        raise ImportDataError("зайві поля у рядку", line_number=line_number)
    missing = [name for name in REQUIRED_COLUMNS if row.get(name) is None]
    if missing:
        raise ImportDataError(
            f"відсутні поля: {', '.join(missing)}", line_number=line_number
        )
    try:
        student = Student(
            student_id=parse_student_id(str(row["student_id"])),
            first_name=str(row["first_name"]),
            last_name=str(row["last_name"]),
            group=str(row["group"]),
            average_grade=parse_average_grade(str(row["average_grade"])),
        )
    except ValidationError as error:
        raise ImportDataError(str(error), line_number=line_number) from error
    if allowed_groups and student.group not in allowed_groups:
        raise ImportDataError(
            f"група {student.group} не дозволена", line_number=line_number
        )
    return student


def read_students_csv(
    path: Path,
    *,
    skip_invalid: bool = True,
    allowed_groups: frozenset[str] = frozenset(),
) -> ImportResult:
    """Читає CSV; некоректні рядки пропускає або (strict) зупиняє імпорт."""
    allowed = frozenset(normalize_group(group) for group in allowed_groups)
    result = ImportResult()
    seen: set[int] = set()
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            columns = reader.fieldnames or []
            missing = [
                name for name in REQUIRED_COLUMNS if name not in columns
            ]
            if missing:
                raise ImportDataError(
                    f"у файлі немає колонок: {', '.join(missing)}"
                )
            for row in reader:
                line_number = reader.line_num
                try:
                    student = parse_row(row, line_number, allowed)
                    if student.student_id in seen:
                        raise ImportDataError(
                            f"дублікат student_id {student.student_id}",
                            line_number=line_number,
                        )
                except ImportDataError as error:
                    if not skip_invalid:
                        raise
                    result.issues.append(
                        ImportIssue(line_number, error.detail)
                    )
                    continue
                seen.add(student.student_id)
                result.students.append(student)
    except (OSError, UnicodeDecodeError) as error:
        raise ImportDataError(
            f"не вдалося прочитати {path.name}: {error}"
        ) from error
    return result
