import itertools
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest.mock import create_autospec

import pytest

from student_app.config import ENV_NAMES, ENV_PREFIX
from student_app.models import Student
from student_app.repositories import InMemoryStudentRepository
from student_app.services import Notifier, StudentService

StudentFactory = Callable[..., Student]
CsvWriter = Callable[..., Path]
ConfigWriter = Callable[..., Path]

CSV_HEADER = "student_id,first_name,last_name,group,grades"


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(ENV_PREFIX + name, raising=False)


@pytest.fixture(scope="session")
def allowed_groups() -> frozenset[str]:
    return frozenset({"PI-21", "PI-22", "PI-23"})


@pytest.fixture
def student_factory() -> StudentFactory:
    counter = itertools.count(1)

    def create(
        last_name: str = "Коваленко",
        first_name: str = "Олена",
        group: str = "PI-21",
        grades: tuple[float, ...] = (90.0,),
        student_id: int | None = None,
    ) -> Student:
        identifier = next(counter) if student_id is None else student_id
        return Student(identifier, first_name, last_name, group, grades)

    return create


@pytest.fixture
def repository() -> InMemoryStudentRepository:
    return InMemoryStudentRepository()


@pytest.fixture
def notifier() -> Notifier:
    return create_autospec(Notifier, instance=True)


@pytest.fixture
def service(repository: InMemoryStudentRepository, notifier: Notifier) -> StudentService:
    return StudentService(repository, notifier, pass_threshold=60.0)


@pytest.fixture
def populated_service(
    repository: InMemoryStudentRepository, service: StudentService, student_factory: StudentFactory
) -> StudentService:
    repository.add(student_factory("Коваленко", "Олена", "PI-21", (95.0, 92.0, 98.0), 1))
    repository.add(student_factory("Мельник", "Андрій", "PI-21", (78.0, 81.0, 74.0), 2))
    repository.add(student_factory("Бондар", "Ірина", "PI-22", (100.0, 99.5), 3))
    repository.add(student_factory("Гриценко", "Тарас", "PI-22", (55.0, 48.0, 62.0), 4))
    repository.add(student_factory("Гнатюк", "Софія", "PI-23", (), 5))
    return service


@pytest.fixture
def csv_writer(tmp_path: Path) -> CsvWriter:
    def write(*rows: str, name: str = "students.csv", header: str = CSV_HEADER) -> Path:
        path = tmp_path / name
        path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
        return path

    return write


@pytest.fixture
def config_writer(tmp_path: Path) -> ConfigWriter:
    def write(text: str | None = None, **overrides: str) -> Path:
        lines = {
            "input_path": "students.csv",
            "output_path": "output/report.json",
            "skip_invalid": "true",
            "pass_threshold": "60",
        } | overrides
        body = text if text is not None else "".join(f"{k}: {v}\n" for k, v in lines.items())
        path = tmp_path / "config.yaml"
        path.write_text(body, encoding="utf-8")
        return path

    return write


@pytest.fixture
def output_dir(tmp_path: Path) -> Iterator[Path]:
    directory = tmp_path / "output"
    yield directory
    leftovers = list(directory.glob("*.tmp")) if directory.exists() else []
    assert leftovers == [], f"тимчасові файли не видалено: {leftovers}"
