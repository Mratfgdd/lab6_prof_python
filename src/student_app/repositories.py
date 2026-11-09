import asyncio
from typing import Protocol

from student_app.exceptions import DuplicateStudentError, StudentNotFoundError
from student_app.models import Student


class StudentRepository(Protocol):
    def add(self, student: Student) -> None: ...

    def update(self, student: Student) -> None: ...

    def get(self, student_id: int) -> Student | None: ...

    def find_by_last_name(self, last_name: str) -> list[Student]: ...

    def all(self) -> list[Student]: ...


class AsyncStudentRepository(Protocol):
    async def get(self, student_id: int) -> Student | None: ...

    async def all(self) -> list[Student]: ...


class InMemoryStudentRepository:
    def __init__(self) -> None:
        self._items: dict[int, Student] = {}

    def add(self, student: Student) -> None:
        if student.student_id in self._items:
            raise DuplicateStudentError(f"студент {student.student_id} уже існує")
        self._items[student.student_id] = student

    def update(self, student: Student) -> None:
        if student.student_id not in self._items:
            raise StudentNotFoundError(f"студента {student.student_id} не знайдено")
        self._items[student.student_id] = student

    def get(self, student_id: int) -> Student | None:
        return self._items.get(student_id)

    def find_by_last_name(self, last_name: str) -> list[Student]:
        wanted = last_name.strip().casefold()
        return [s for s in self._items.values() if s.last_name.casefold() == wanted]

    def all(self) -> list[Student]:
        return list(self._items.values())


class InMemoryAsyncStudentRepository:
    def __init__(self, students: list[Student] | None = None) -> None:
        self._items = {student.student_id: student for student in students or []}

    async def get(self, student_id: int) -> Student | None:
        await asyncio.sleep(0)
        return self._items.get(student_id)

    async def all(self) -> list[Student]:
        await asyncio.sleep(0)
        return list(self._items.values())
