class StudentAppError(Exception):
    pass


class InvalidStudentError(StudentAppError, ValueError):
    pass


class InvalidGradeError(StudentAppError, ValueError):
    pass


class EmptyGradesError(StudentAppError, ValueError):
    pass


class DuplicateStudentError(StudentAppError):
    pass


class StudentNotFoundError(StudentAppError, LookupError):
    pass


class NoStudentsError(StudentAppError):
    pass


class NotificationError(StudentAppError):
    pass


class RepositoryError(StudentAppError):
    pass


class ImportDataError(StudentAppError):
    def __init__(self, message: str, *, line_number: int | None = None) -> None:
        text = message if line_number is None else f"рядок {line_number}: {message}"
        super().__init__(text)
        self.detail = message
        self.line_number = line_number


class ExportError(StudentAppError):
    pass


class ConfigurationError(StudentAppError):
    pass
