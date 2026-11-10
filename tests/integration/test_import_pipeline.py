"""Integration: CSV -> валідація -> реєстрація студентів -> звіт."""

import pytest
from support import (
    ConfigWriter,
    CsvWriter,
    FakeStudentRepository,
    RecordingNotifier,
)

from student_manager.config import load_config
from student_manager.exceptions import ImportDataError
from student_manager.importers import read_students_csv
from student_manager.reports import build_report
from student_manager.repositories import InMemoryStudentRepository
from student_manager.services import StudentService

pytestmark = pytest.mark.integration


def test_import_registers_valid_students_and_reports_malformed_ones(
    csv_writer: CsvWriter,
) -> None:
    path = csv_writer(
        "1,Олена,Коваленко,PI-21,95",
        "2,Андрій,Мельник,PI-21,abc",
        "3,Ірина,Бондар,PI-22,99.5",
        "4,Тарас,Гриценко,PI-22,52.5",
    )
    imported = read_students_csv(path)
    notifier = RecordingNotifier()
    service = StudentService(InMemoryStudentRepository(), notifier)
    for student in imported.students:
        service.register(student)
    assert [issue.line_number for issue in imported.issues] == [3]
    assert [s.student_id for s in service.all_students()] == [1, 3, 4]
    assert [student_id for student_id, _ in notifier.sent] == [1, 3, 4]


def test_import_validation_report_chain(csv_writer: CsvWriter) -> None:
    path = csv_writer(
        "1,Олена,Коваленко,PI-21,95",
        "2,Андрій,Мельник,PI-21,78",
        "3,Ірина,Бондар,PI-22,99.5",
        "4,Тарас,Гриценко,PI-22,48.75",
    )
    service = StudentService(FakeStudentRepository(), RecordingNotifier())
    for student in read_students_csv(path).students:
        service.register(student)
    report = build_report(service.all_students(), pass_threshold=60.0)
    assert report["best_student"]["name"] == "Ірина Бондар"
    assert report["at_risk"] == [4]
    assert report["groups"][0] == {
        "group": "PI-21",
        "students": 2,
        "average_grade": 86.5,
    }
    assert report["levels"]["unsatisfactory"] == 1


def test_allowed_groups_from_yaml_filter_the_import(
    csv_writer: CsvWriter, config_writer: ConfigWriter
) -> None:
    csv_writer("1,Олена,Коваленко,PI-21,95", "2,Анна,Коваль,PI-24,90")
    config = load_config(config_writer(allowed_groups="[PI-21, PI-22]"))
    imported = read_students_csv(
        config.input_path,
        skip_invalid=config.skip_invalid,
        allowed_groups=config.allowed_groups,
    )
    assert [s.student_id for s in imported.students] == [1]
    assert imported.issues[0].message == "група PI-24 не дозволена"


def test_strict_import_aborts_and_releases_the_input_file(
    csv_writer: CsvWriter,
) -> None:
    path = csv_writer("1,Олена,Коваленко,PI-21,95", "2,Андрій,,PI-21,80")
    with pytest.raises(ImportDataError, match="рядок 3"):
        read_students_csv(path, skip_invalid=False)
    path.unlink()
    assert not path.exists()
