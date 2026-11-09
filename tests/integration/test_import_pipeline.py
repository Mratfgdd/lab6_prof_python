import pytest
from conftest import CsvWriter
from fakes import FakeStudentRepository, RecordingNotifier

from student_app.exceptions import ImportDataError
from student_app.files import read_students_csv
from student_app.reports import build_report
from student_app.repositories import InMemoryStudentRepository
from student_app.services import StudentService

pytestmark = pytest.mark.integration


def test_csv_import_registers_valid_students_and_reports_malformed_ones(
    csv_writer: CsvWriter,
) -> None:
    path = csv_writer(
        "1,Олена,Коваленко,PI-21,95;92",
        "2,Андрій,Мельник,PI-21,abc",
        "3,Ірина,Бондар,PI-22,100;99",
        "4,Тарас,Гриценко,PI-22,50;55",
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
        "1,Олена,Коваленко,PI-21,95;92;98",
        "2,Андрій,Мельник,PI-21,78;81;74",
        "3,Ірина,Бондар,PI-22,100;99.5",
        "4,Тарас,Гриценко,PI-22,55;48;62",
    )
    repository = FakeStudentRepository()
    service = StudentService(repository, RecordingNotifier())
    for student in read_students_csv(path).students:
        service.register(student)
    report = build_report(service.all_students(), pass_threshold=60.0)
    assert report["best_student"]["name"] == "Бондар Ірина"
    assert report["at_risk"] == [4]
    assert report["groups"][0] == {"group": "PI-21", "students": 2, "average": 86.33}
    assert report["levels"]["unsatisfactory"] == 1


def test_strict_import_aborts_and_releases_the_input_file(csv_writer: CsvWriter) -> None:
    path = csv_writer("1,Олена,Коваленко,PI-21,95", "2,Андрій,,PI-21,80")
    with pytest.raises(ImportDataError, match="рядок 3"):
        read_students_csv(path, skip_invalid=False)
    path.unlink()
    assert not path.exists()
