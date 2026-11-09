from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any

from student_app.exceptions import NoStudentsError
from student_app.grading import LEVELS
from student_app.models import Student


def best_of(students: Iterable[Student]) -> Student:
    graded = [student for student in students if student.grades]
    if not graded:
        raise NoStudentsError("немає студентів з оцінками")
    return max(graded, key=lambda student: (student.average, -student.student_id))


def average_or_none(students: Iterable[Student]) -> float | None:
    averages = [student.average for student in students if student.grades]
    if not averages:
        return None
    return sum(averages) / len(averages)


def level_counts(students: Iterable[Student]) -> dict[str, int]:
    counts = Counter(student.level for student in students if student.grades)
    return {level: counts[level] for level in LEVELS}


def rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def build_report(students: Sequence[Student], *, pass_threshold: float) -> dict[str, Any]:
    graded = [student for student in students if student.grades]
    groups = []
    for group in sorted({student.group for student in students}):
        members = [student for student in students if student.group == group]
        groups.append(
            {
                "group": group,
                "students": len(members),
                "average": rounded(average_or_none(members)),
            }
        )
    best = best_of(graded) if graded else None
    return {
        "total_students": len(students),
        "graded_students": len(graded),
        "average_grade": rounded(average_or_none(students)),
        "best_student": None
        if best is None
        else {
            "student_id": best.student_id,
            "name": best.full_name,
            "group": best.group,
            "average": rounded(best.average),
        },
        "groups": groups,
        "levels": level_counts(students),
        "at_risk": sorted(s.student_id for s in graded if s.average < pass_threshold),
    }
