from student_app.models import Student


class FakeStudentRepository:
    def __init__(self) -> None:
        self.items: dict[int, Student] = {}

    def add(self, student: Student) -> None:
        self.items[student.student_id] = student

    def update(self, student: Student) -> None:
        self.items[student.student_id] = student

    def get(self, student_id: int) -> Student | None:
        return self.items.get(student_id)

    def find_by_last_name(self, last_name: str) -> list[Student]:
        return [s for s in self.items.values() if s.last_name == last_name]

    def all(self) -> list[Student]:
        return list(self.items.values())


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    def send(self, student: Student, message: str) -> None:
        self.sent.append((student.student_id, message))
