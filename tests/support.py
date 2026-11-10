"""Типи фабрик і тестові двійники (Fake, Spy) для набору тестів."""

from collections.abc import Callable
from pathlib import Path

from student_manager.models import Student

StudentFactory = Callable[..., Student]
CsvWriter = Callable[..., Path]
ConfigWriter = Callable[..., Path]

STUDENT_ROWS = (
    "1,Олена,Коваленко,PI-21,95.0",
    "2,Андрій,Мельник,PI-21,78.0",
    "3,Ірина,Бондар,PI-22,99.5",
    "4,Тарас,Гриценко,PI-22,48.75",
    "5,Софія,Гнатюк,PI-23,71.0",
    "6,Дмитро,Бойко,PI-21,abc",
    "7,Катерина,Шевчук,PI-24,90",
)


class FakeStudentRepository:
    """Fake: працююче сховище у словнику, без перевірок дублікатів."""

    def __init__(self) -> None:
        """Створює порожнє сховище."""
        self.items: dict[int, Student] = {}

    def add(self, student: Student) -> None:
        """Зберігає студента."""
        self.items[student.student_id] = student

    def update(self, student: Student) -> None:
        """Замінює студента."""
        self.items[student.student_id] = student

    def get(self, student_id: int) -> Student | None:
        """Повертає студента або None."""
        return self.items.get(student_id)

    def find_by_last_name(self, last_name: str) -> list[Student]:
        """Точний збіг прізвища."""
        return [s for s in self.items.values() if s.last_name == last_name]

    def all(self) -> list[Student]:
        """Усі студенти."""
        return list(self.items.values())


class RecordingNotifier:
    """Spy: запам'ятовує, кому й що було надіслано."""

    def __init__(self) -> None:
        """Створює порожній журнал надісланих повідомлень."""
        self.sent: list[tuple[int, str]] = []

    def send(self, student: Student, message: str) -> None:
        """Записує пару (ідентифікатор студента, текст)."""
        self.sent.append((student.student_id, message))
