import random

from student_app.models import Student
from student_app.repositories import InMemoryStudentRepository


def register_students(student_ids: list[int]) -> InMemoryStudentRepository:
    repository = InMemoryStudentRepository()
    for student_id in student_ids:
        repository.add(Student(student_id, "Олена", "Коваленко", "PI-21", (90.0,)))
    return repository


def test_flaky_random_student_ids() -> None:
    student_ids = [random.randint(1, 4) for _ in range(2)]
    assert len(register_students(student_ids).all()) == 2


def test_deterministic_student_ids() -> None:
    rng = random.Random(2026)
    student_ids = rng.sample(range(1, 5), k=2)
    assert len(register_students(student_ids).all()) == 2
