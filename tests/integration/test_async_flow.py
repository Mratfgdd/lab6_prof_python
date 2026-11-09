import pytest
from conftest import CsvWriter

from student_app.exceptions import StudentNotFoundError
from student_app.files import read_students_csv
from student_app.reports import build_report
from student_app.repositories import InMemoryAsyncStudentRepository
from student_app.services import AsyncStudentService

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_imported_students_are_served_by_async_service(csv_writer: CsvWriter) -> None:
    path = csv_writer(
        "1,Олена,Коваленко,PI-21,95;92",
        "2,Андрій,Мельник,PI-21,70;75",
        "3,Ірина,Бондар,PI-22,100;99",
    )
    students = read_students_csv(path).students
    service = AsyncStudentService(InMemoryAsyncStudentRepository(students))
    loaded = await service.load_many([3, 1])
    assert [s.last_name for s in loaded] == ["Бондар", "Коваленко"]
    best = await service.best_student()
    report = build_report(students, pass_threshold=60.0)
    assert best.student_id == report["best_student"]["student_id"] == 3
    with pytest.raises(StudentNotFoundError):
        await service.load(99)
