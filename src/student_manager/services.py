"""Бізнес-логіка: пошук, фільтрація, статистика та сервіси студентів."""

import asyncio
import logging
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Protocol

from student_manager.exceptions import (
    NoStudentsError,
    NotificationError,
    RepositoryError,
    StudentNotFoundError,
)
from student_manager.models import LEVELS, Student
from student_manager.repositories import (
    AsyncStudentRepository,
    StudentRepository,
)
from student_manager.validators import (
    normalize_group,
    validate_average_grade,
)

logger = logging.getLogger(__name__)


def filter_by_group(students: Iterable[Student], group: str) -> list[Student]:
    """Повертає студентів однієї групи; код групи нормалізується."""
    wanted = normalize_group(group)
    return [student for student in students if student.group == wanted]


def find_by_last_name(
    students: Iterable[Student], last_name: str
) -> list[Student]:
    """Шукає за прізвищем без урахування регістру й крайніх пробілів."""
    wanted = last_name.strip().casefold()
    return [s for s in students if s.last_name.casefold() == wanted]


def find_by_id(students: Iterable[Student], student_id: int) -> Student | None:
    """Повертає студента з цим ідентифікатором або None."""
    return next((s for s in students if s.student_id == student_id), None)


def calculate_group_average(students: Sequence[Student]) -> float:
    """Середнє арифметичне середніх балів; порожня колекція заборонена."""
    if not students:
        raise NoStudentsError("неможливо обчислити середній бал без студентів")
    return sum(student.average_grade for student in students) / len(students)


def find_best_student(students: Iterable[Student]) -> Student:
    """Студент із найвищим балом; при рівності - з меншим ідентифікатором."""
    candidates = list(students)
    if not candidates:
        raise NoStudentsError("немає студентів для вибору найкращого")
    return max(candidates, key=lambda s: (s.average_grade, -s.student_id))


def count_by_level(students: Iterable[Student]) -> dict[str, int]:
    """Кількість студентів на кожному рівні успішності."""
    counts = Counter(student.level for student in students)
    return {level: counts[level] for level in LEVELS}


class Notifier(Protocol):
    """Канал сповіщень студентів (пошта, месенджер тощо)."""

    def send(self, student: Student, message: str) -> None:
        """Надсилає повідомлення; при збої піднімає NotificationError."""


class LoggingNotifier:
    """Сповіщувач за замовчуванням: записує повідомлення в журнал."""

    def send(self, student: Student, message: str) -> None:
        """Записує повідомлення в журнал на рівні INFO."""
        logger.info("Сповіщення студенту %s: %s", student.student_id, message)


class StudentService:
    """Реєстрація студентів, оновлення балів і статистика."""

    def __init__(
        self,
        repository: StudentRepository,
        notifier: Notifier,
        pass_threshold: float = 60.0,
    ) -> None:
        """Приймає сховище й сповіщувач ззовні (dependency injection)."""
        self._repository = repository
        self._notifier = notifier
        self._pass_threshold = validate_average_grade(pass_threshold)
        self.failed_notifications: list[int] = []

    def register(self, student: Student) -> Student:
        """Зберігає студента й надсилає йому вітальне повідомлення."""
        self._repository.add(student)
        self._notify(student, f"Вас зараховано до групи {student.group}")
        return student

    def get(self, student_id: int) -> Student:
        """Повертає студента за ідентифікатором."""
        student = self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(f"студента {student_id} не знайдено")
        return student

    def find_by_last_name(self, last_name: str) -> list[Student]:
        """Шукає за прізвищем; результат відсортовано за ідентифікатором."""
        found = self._repository.find_by_last_name(last_name)
        return sorted(found, key=lambda student: student.student_id)

    def all_students(self) -> list[Student]:
        """Усі студенти, відсортовані за ідентифікатором."""
        return sorted(self._repository.all(), key=lambda s: s.student_id)

    def by_group(self, group: str) -> list[Student]:
        """Студенти групи, відсортовані за прізвищем та ідентифікатором."""
        members = filter_by_group(self._repository.all(), group)
        return sorted(members, key=lambda s: (s.last_name, s.student_id))

    def update_average_grade(
        self, student_id: int, average_grade: float
    ) -> Student:
        """Змінює середній бал; нижче порогу - сповіщає студента."""
        updated = self.get(student_id).with_average_grade(average_grade)
        self._repository.update(updated)
        if updated.average_grade < self._pass_threshold:
            self._notify(
                updated,
                f"Середній бал {updated.average_grade:.2f} "
                f"нижчий за {self._pass_threshold:g}",
            )
        return updated

    def best_student(self) -> Student:
        """Студент із найвищим середнім балом."""
        return find_best_student(self._repository.all())

    def group_average(self, group: str) -> float:
        """Середній бал групи."""
        members = self.by_group(group)
        if not members:
            raise NoStudentsError(
                f"у групі {normalize_group(group)} немає студентів"
            )
        return calculate_group_average(members)

    def level_distribution(self) -> dict[str, int]:
        """Розподіл студентів за рівнями успішності."""
        return count_by_level(self._repository.all())

    def _notify(self, student: Student, message: str) -> None:
        """Надсилає повідомлення; збій сповіщення не скасовує операцію."""
        try:
            self._notifier.send(student, message)
        except NotificationError:
            logger.warning(
                "Не вдалося сповістити студента %s", student.student_id
            )
            self.failed_notifications.append(student.student_id)


class AsyncStudentService:
    """Асинхронний доступ до студентів через AsyncStudentRepository."""

    def __init__(self, repository: AsyncStudentRepository) -> None:
        """Приймає асинхронне сховище ззовні."""
        self._repository = repository

    async def load(self, student_id: int) -> Student:
        """Завантажує студента; збій з'єднання стає RepositoryError."""
        try:
            student = await self._repository.get(student_id)
        except ConnectionError as error:
            raise RepositoryError(f"сховище недоступне: {error}") from error
        if student is None:
            raise StudentNotFoundError(f"студента {student_id} не знайдено")
        return student

    async def load_many(self, student_ids: list[int]) -> list[Student]:
        """Завантажує студентів паралельно; порядок збігається з id-ами."""
        tasks = (self.load(student_id) for student_id in student_ids)
        return list(await asyncio.gather(*tasks))

    async def best_student(self) -> Student:
        """Знаходить найкращого студента серед усіх у сховищі."""
        try:
            students = await self._repository.all()
        except ConnectionError as error:
            raise RepositoryError(f"сховище недоступне: {error}") from error
        return find_best_student(students)
