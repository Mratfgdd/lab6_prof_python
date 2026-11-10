"""Зведений звіт по студентах для експорту в JSON."""

from collections.abc import Sequence
from typing import Any

from student_manager.models import Student
from student_manager.services import (
    calculate_group_average,
    count_by_level,
    filter_by_group,
    find_best_student,
)


def rounded(value: float | None) -> float | None:
    """Округлює до сотих; None залишається None."""
    return None if value is None else round(value, 2)


def build_report(
    students: Sequence[Student], *, pass_threshold: float
) -> dict[str, Any]:
    """Будує звіт: кількість, середній бал, найкращий, групи, ризик."""
    groups = []
    for group in sorted({student.group for student in students}):
        members = filter_by_group(students, group)
        groups.append(
            {
                "group": group,
                "students": len(members),
                "average_grade": rounded(calculate_group_average(members)),
            }
        )
    best = find_best_student(students) if students else None
    return {
        "total_students": len(students),
        "average_grade": rounded(
            calculate_group_average(students) if students else None
        ),
        "best_student": None
        if best is None
        else {
            "student_id": best.student_id,
            "name": best.full_name,
            "group": best.group,
            "average_grade": rounded(best.average_grade),
        },
        "groups": groups,
        "levels": count_by_level(students),
        "at_risk": sorted(
            student.student_id
            for student in students
            if student.average_grade < pass_threshold
        ),
    }
