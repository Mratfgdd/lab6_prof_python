import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from student_app.config import AppConfig, load_config
from student_app.exceptions import StudentAppError
from student_app.files import read_students_csv, write_json
from student_app.reports import build_report
from student_app.repositories import InMemoryStudentRepository
from student_app.services import LoggingNotifier, Notifier, StudentService


def run_pipeline(config: AppConfig, notifier: Notifier | None = None) -> dict[str, Any]:
    imported = read_students_csv(
        config.input_path,
        skip_invalid=config.skip_invalid,
        allowed_groups=config.allowed_groups,
    )
    service = StudentService(
        InMemoryStudentRepository(), notifier or LoggingNotifier(), config.pass_threshold
    )
    for student in imported.students:
        service.register(student)
    report = build_report(service.all_students(), pass_threshold=config.pass_threshold)
    report["import_errors"] = [
        {"line": issue.line_number, "message": issue.message} for issue in imported.issues
    ]
    write_json(config.output_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Звіт по успішності студентів")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        report = run_pipeline(config)
    except StudentAppError as error:
        print(f"Помилка: {error}", file=sys.stderr)
        return 1
    best = report["best_student"]
    print(
        f"Студентів: {report['total_students']}, помилок імпорту: {len(report['import_errors'])}, "
        f"найкращий: {best['name'] if best else '—'}, звіт: {config.output_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
