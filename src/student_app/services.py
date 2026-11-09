import asyncio
import logging
from typing import Protocol

from student_app.exceptions import (
    NoStudentsError,
    NotificationError,
    RepositoryError,
    StudentNotFoundError,
)
from student_app.models import Student, normalize_group
from student_app.reports import average_or_none, best_of, level_counts
from student_app.repositories import AsyncStudentRepository, StudentRepository

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def send(self, student: Student, message: str) -> None: ...


class LoggingNotifier:
    def send(self, student: Student, message: str) -> None:
        logger.info("Сповіщення студенту %s: %s", student.student_id, message)


class StudentService:
    def __init__(
        self, repository: StudentRepository, notifier: Notifier, pass_threshold: float = 60.0
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._pass_threshold = pass_threshold
        self.failed_notifications: list[int] = []

    def register(self, student: Student) -> Student:
        self._repository.add(student)
        self._notify(student, f"Вас зараховано до групи {student.group}")
        return student

    def get(self, student_id: int) -> Student:
        student = self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(f"студента {student_id} не знайдено")
        return student

    def find_by_last_name(self, last_name: str) -> list[Student]:
        return sorted(
            self._repository.find_by_last_name(last_name), key=lambda student: student.student_id
        )

    def all_students(self) -> list[Student]:
        return sorted(self._repository.all(), key=lambda student: student.student_id)

    def by_group(self, group: str) -> list[Student]:
        wanted = normalize_group(group)
        members = [student for student in self._repository.all() if student.group == wanted]
        return sorted(members, key=lambda student: (student.last_name, student.student_id))

    def add_grade(self, student_id: int, grade: float) -> Student:
        updated = self.get(student_id).with_grade(grade)
        self._repository.update(updated)
        if updated.average < self._pass_threshold:
            self._notify(
                updated, f"Середній бал {updated.average:.2f} нижчий за {self._pass_threshold:g}"
            )
        return updated

    def best_student(self) -> Student:
        return best_of(self._repository.all())

    def group_average(self, group: str) -> float:
        average = average_or_none(self.by_group(group))
        if average is None:
            raise NoStudentsError(f"у групі {group} немає студентів з оцінками")
        return average

    def level_distribution(self) -> dict[str, int]:
        return level_counts(self._repository.all())

    def _notify(self, student: Student, message: str) -> None:
        try:
            self._notifier.send(student, message)
        except NotificationError:
            logger.warning("Не вдалося сповістити студента %s", student.student_id)
            self.failed_notifications.append(student.student_id)


class AsyncStudentService:
    def __init__(self, repository: AsyncStudentRepository) -> None:
        self._repository = repository

    async def load(self, student_id: int) -> Student:
        try:
            student = await self._repository.get(student_id)
        except ConnectionError as error:
            raise RepositoryError(f"сховище недоступне: {error}") from error
        if student is None:
            raise StudentNotFoundError(f"студента {student_id} не знайдено")
        return student

    async def load_many(self, student_ids: list[int]) -> list[Student]:
        return list(await asyncio.gather(*(self.load(student_id) for student_id in student_ids)))

    async def best_student(self) -> Student:
        try:
            students = await self._repository.all()
        except ConnectionError as error:
            raise RepositoryError(f"сховище недоступне: {error}") from error
        return best_of(students)
