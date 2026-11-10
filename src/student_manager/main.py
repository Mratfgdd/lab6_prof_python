"""Точка входу: CSV -> валідація -> реєстрація -> звіт у JSON."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from student_manager.config import AppConfig, load_config
from student_manager.exceptions import StudentManagerError
from student_manager.exporters import write_json
from student_manager.importers import read_students_csv
from student_manager.reports import build_report
from student_manager.repositories import InMemoryStudentRepository
from student_manager.services import LoggingNotifier, Notifier, StudentService


def run_pipeline(
    config: AppConfig, notifier: Notifier | None = None
) -> dict[str, Any]:
    """Імпортує студентів, реєструє їх, будує звіт і записує його в JSON."""
    imported = read_students_csv(
        config.input_path,
        skip_invalid=config.skip_invalid,
        allowed_groups=config.allowed_groups,
    )
    service = StudentService(
        InMemoryStudentRepository(),
        notifier or LoggingNotifier(),
        config.pass_threshold,
    )
    for student in imported.students:
        service.register(student)
    report = build_report(
        service.all_students(), pass_threshold=config.pass_threshold
    )
    report["import_errors"] = [
        {"line": issue.line_number, "message": issue.message}
        for issue in imported.issues
    ]
    write_json(config.output_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Запускає застосунок; повертає код завершення (0 - успіх)."""
    parser = argparse.ArgumentParser(
        description="Звіт по успішності студентів"
    )
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        report = run_pipeline(config)
    except StudentManagerError as error:
        print(f"Помилка: {error}", file=sys.stderr)
        return 1
    best = report["best_student"]
    print(
        f"Студентів: {report['total_students']}, "
        f"помилок імпорту: {len(report['import_errors'])}, "
        f"найкращий: {best['name'] if best else '—'}, "
        f"звіт: {config.output_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
