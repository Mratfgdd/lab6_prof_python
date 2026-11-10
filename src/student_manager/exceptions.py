"""Винятки предметної області системи обліку студентів."""


class StudentManagerError(Exception):
    """Базовий виняток застосунку."""


class ValidationError(StudentManagerError, ValueError):
    """Некоректне значення поля; атрибут field вказує, якого саме."""

    def __init__(self, message: str, *, field: str) -> None:
        """Зберігає повідомлення й назву поля, у якому знайдено помилку."""
        super().__init__(message)
        self.field = field


class InvalidStudentError(ValidationError):
    """Некоректний ідентифікатор, ім'я або група студента."""


class InvalidGradeError(ValidationError):
    """Середній бал не є числом від 0 до 100."""

    def __init__(self, message: str) -> None:
        """Створює помилку для поля average_grade."""
        super().__init__(message, field="average_grade")


class DuplicateStudentError(StudentManagerError):
    """Студент з таким ідентифікатором уже існує."""


class StudentNotFoundError(StudentManagerError, LookupError):
    """Студента не знайдено."""


class NoStudentsError(StudentManagerError):
    """Операція потребує хоча б одного студента, а колекція порожня."""


class NotificationError(StudentManagerError):
    """Не вдалося надіслати сповіщення студенту."""


class RepositoryError(StudentManagerError):
    """Сховище студентів недоступне."""


class ImportDataError(StudentManagerError):
    """Файл імпорту не можна прочитати або рядок у ньому некоректний."""

    def __init__(
        self, message: str, *, line_number: int | None = None
    ) -> None:
        """Додає номер рядка до тексту, якщо він відомий."""
        text = (
            message
            if line_number is None
            else f"рядок {line_number}: {message}"
        )
        super().__init__(text)
        self.detail = message
        self.line_number = line_number


class ExportError(StudentManagerError):
    """Не вдалося записати файл експорту."""


class ConfigurationError(StudentManagerError):
    """Конфігурація відсутня або містить некоректні параметри."""
