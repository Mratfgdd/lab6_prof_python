import csv
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from student_app.exceptions import (
    ExportError,
    ImportDataError,
    InvalidGradeError,
    InvalidStudentError,
)
from student_app.models import Student, normalize_group

REQUIRED_COLUMNS = ("student_id", "first_name", "last_name", "group", "grades")
GRADE_SEPARATOR = ";"


@dataclass(frozen=True)
class ImportIssue:
    line_number: int
    message: str


@dataclass
class ImportResult:
    students: list[Student] = field(default_factory=list)
    issues: list[ImportIssue] = field(default_factory=list)


def parse_grades(raw: str) -> tuple[float, ...]:
    parts = [part.strip() for part in raw.split(GRADE_SEPARATOR) if part.strip()]
    return tuple(float(part) for part in parts)


def parse_row(
    row: Mapping[str | None, Any], line_number: int, allowed_groups: frozenset[str]
) -> Student:
    if None in row:
        raise ImportDataError("зайві поля у рядку", line_number=line_number)
    missing = [name for name in REQUIRED_COLUMNS if row.get(name) is None]
    if missing:
        raise ImportDataError(f"відсутні поля: {', '.join(missing)}", line_number=line_number)
    try:
        student = Student(
            student_id=int(row["student_id"]),
            first_name=row["first_name"],
            last_name=row["last_name"],
            group=row["group"],
            grades=parse_grades(row["grades"]),
        )
    except InvalidGradeError as error:
        raise ImportDataError(f"некоректна оцінка: {error}", line_number=line_number) from error
    except InvalidStudentError as error:
        raise ImportDataError(f"некоректний студент: {error}", line_number=line_number) from error
    except ValueError as error:
        raise ImportDataError(f"некоректне число: {error}", line_number=line_number) from error
    if allowed_groups and student.group not in allowed_groups:
        raise ImportDataError(f"група {student.group} не дозволена", line_number=line_number)
    return student


def read_students_csv(
    path: Path, *, skip_invalid: bool = True, allowed_groups: frozenset[str] = frozenset()
) -> ImportResult:
    allowed = frozenset(normalize_group(group) for group in allowed_groups)
    result = ImportResult()
    seen: set[int] = set()
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            missing = [name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or [])]
            if missing:
                raise ImportDataError(f"у файлі немає колонок: {', '.join(missing)}")
            for row in reader:
                line_number = reader.line_num
                try:
                    student = parse_row(row, line_number, allowed)
                    if student.student_id in seen:
                        raise ImportDataError(
                            f"дублікат student_id {student.student_id}", line_number=line_number
                        )
                except ImportDataError as error:
                    if not skip_invalid:
                        raise
                    result.issues.append(ImportIssue(line_number, error.detail))
                    continue
                seen.add(student.student_id)
                result.students.append(student)
    except (OSError, UnicodeDecodeError) as error:
        raise ImportDataError(f"не вдалося прочитати {path.name}: {error}") from error
    return result


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    except (OSError, TypeError) as error:
        temporary.unlink(missing_ok=True)
        raise ExportError(f"не вдалося записати {path.name}: {error}") from error
