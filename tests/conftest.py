"""Спільні fixtures: pytest знаходить файл сам, імпортувати їх не потрібно."""

import itertools
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest
from support import ConfigWriter, CsvWriter, StudentFactory

from student_manager.config import ENV_NAMES, ENV_PREFIX
from student_manager.models import Student
from student_manager.repositories import InMemoryStudentRepository
from student_manager.services import Notifier, StudentService

CSV_HEADER = "student_id,first_name,last_name,group,average_grade"


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Прибирає змінні середовища застосунку, щоб тести не залежали від ОС."""
    for name in ENV_NAMES:
        monkeypatch.delenv(ENV_PREFIX + name, raising=False)


@pytest.fixture(scope="session")
def allowed_groups() -> frozenset[str]:
    """Незмінний набір дозволених груп; безпечно ділити на всю сесію."""
    return frozenset({"PI-21", "PI-22", "PI-23"})


@pytest.fixture(params=["utf-8", "utf-8-sig"])
def csv_encoding(request: pytest.FixtureRequest) -> str:
    """Параметризована fixture: кодування з BOM і без нього."""
    return str(request.param)


@pytest.fixture
def student_factory() -> StudentFactory:
    """Фабрика студентів: параметри за замовчуванням, унікальні id."""
    counter = itertools.count(1)

    def create(
        last_name: str = "Коваленко",
        first_name: str = "Олена",
        group: str = "PI-21",
        average_grade: float = 90.0,
        student_id: int | None = None,
    ) -> Student:
        identifier = next(counter) if student_id is None else student_id
        return Student(identifier, first_name, last_name, group, average_grade)

    return create


@pytest.fixture
def repository() -> InMemoryStudentRepository:
    """Порожнє сховище в пам'яті для кожного тесту."""
    return InMemoryStudentRepository()


@pytest.fixture
def notifier() -> Mock:
    """Mock із spec: дозволені лише методи протоколу Notifier."""
    return Mock(spec=Notifier)


@pytest.fixture
def service(
    repository: InMemoryStudentRepository, notifier: Mock
) -> StudentService:
    """Сервіс зі справжнім сховищем і підміненим сповіщувачем."""
    return StudentService(repository, notifier, pass_threshold=60.0)


@pytest.fixture
def populated_service(
    repository: InMemoryStudentRepository,
    service: StudentService,
    student_factory: StudentFactory,
) -> StudentService:
    """Сервіс із п'ятьма студентами трьох груп."""
    repository.add(student_factory("Коваленко", "Олена", "PI-21", 95.0, 1))
    repository.add(student_factory("Мельник", "Андрій", "PI-21", 78.0, 2))
    repository.add(student_factory("Бондар", "Ірина", "PI-22", 99.5, 3))
    repository.add(student_factory("Гриценко", "Тарас", "PI-22", 48.75, 4))
    repository.add(student_factory("Гнатюк", "Софія", "PI-23", 71.0, 5))
    return service


@pytest.fixture
def csv_writer(tmp_path: Path) -> CsvWriter:
    """Створює CSV-файл студентів у тимчасовому каталозі."""

    def write(
        *rows: str,
        name: str = "students.csv",
        header: str = CSV_HEADER,
        encoding: str = "utf-8",
    ) -> Path:
        path = tmp_path / name
        text = "\n".join([header, *rows]) + "\n"
        path.write_text(text, encoding=encoding)
        return path

    return write


@pytest.fixture
def config_writer(tmp_path: Path) -> ConfigWriter:
    """Створює config.yaml у тимчасовому каталозі."""

    def write(text: str | None = None, **overrides: str) -> Path:
        lines = {
            "input_path": "students.csv",
            "output_path": "output/report.json",
            "skip_invalid": "true",
            "pass_threshold": "60",
        } | overrides
        body = text
        if body is None:
            body = "".join(f"{key}: {value}\n" for key, value in lines.items())
        path = tmp_path / "config.yaml"
        path.write_text(body, encoding="utf-8")
        return path

    return write


@pytest.fixture
def output_dir(tmp_path: Path) -> Iterator[Path]:
    """Каталог експорту; після тесту перевіряє, що не лишилось *.tmp."""
    directory = tmp_path / "output"
    yield directory
    leftovers = list(directory.glob("*.tmp")) if directory.exists() else []
    assert not leftovers, f"тимчасові файли не видалено: {leftovers}"
