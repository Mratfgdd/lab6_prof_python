"""Сховища студентів: протоколи та реалізації в пам'яті."""

import asyncio
from typing import Protocol

from student_manager.exceptions import (
    DuplicateStudentError,
    StudentNotFoundError,
)
from student_manager.models import Student


class StudentRepository(Protocol):
    """Інтерфейс синхронного сховища студентів."""

    def add(self, student: Student) -> None:
        """Додає нового студента."""

    def update(self, student: Student) -> None:
        """Замінює збереженого студента з тим самим ідентифікатором."""

    def get(self, student_id: int) -> Student | None:
        """Повертає студента за ідентифікатором або None."""

    def find_by_last_name(self, last_name: str) -> list[Student]:
        """Повертає студентів із цим прізвищем."""

    def all(self) -> list[Student]:
        """Повертає всіх студентів."""


class AsyncStudentRepository(Protocol):
    """Інтерфейс асинхронного сховища студентів."""

    async def get(self, student_id: int) -> Student | None:
        """Повертає студента за ідентифікатором або None."""

    async def all(self) -> list[Student]:
        """Повертає всіх студентів."""


class InMemoryStudentRepository:
    """Сховище студентів у словнику."""

    def __init__(self) -> None:
        """Створює порожнє сховище."""
        self._items: dict[int, Student] = {}

    def add(self, student: Student) -> None:
        """Додає студента; повторний ідентифікатор заборонено."""
        if student.student_id in self._items:
            raise DuplicateStudentError(
                f"студент {student.student_id} уже існує"
            )
        self._items[student.student_id] = student

    def update(self, student: Student) -> None:
        """Замінює студента; невідомий ідентифікатор заборонено."""
        if student.student_id not in self._items:
            raise StudentNotFoundError(
                f"студента {student.student_id} не знайдено"
            )
        self._items[student.student_id] = student

    def get(self, student_id: int) -> Student | None:
        """Повертає студента за ідентифікатором або None."""
        return self._items.get(student_id)

    def find_by_last_name(self, last_name: str) -> list[Student]:
        """Шукає за прізвищем без урахування регістру й крайніх пробілів."""
        wanted = last_name.strip().casefold()
        return [
            student
            for student in self._items.values()
            if student.last_name.casefold() == wanted
        ]

    def all(self) -> list[Student]:
        """Повертає копію списку всіх студентів."""
        return list(self._items.values())


class InMemoryAsyncStudentRepository:
    """Асинхронне сховище в пам'яті: віддає керування циклу подій."""

    def __init__(self, students: list[Student] | None = None) -> None:
        """Заповнює сховище переданими студентами."""
        self._items = {
            student.student_id: student for student in students or []
        }

    async def get(self, student_id: int) -> Student | None:
        """Повертає студента за ідентифікатором або None."""
        await asyncio.sleep(0)
        return self._items.get(student_id)

    async def all(self) -> list[Student]:
        """Повертає всіх студентів."""
        await asyncio.sleep(0)
        return list(self._items.values())
