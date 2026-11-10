"""Integration: CLI та асинхронний потік імпорт -> валідація -> звіт."""

from pathlib import Path
from unittest.mock import AsyncMock, create_autospec

import pytest
from support import STUDENT_ROWS, ConfigWriter, CsvWriter

from student_manager.exceptions import RepositoryError, StudentNotFoundError
from student_manager.importers import read_students_csv
from student_manager.main import main
from student_manager.reports import build_report
from student_manager.repositories import (
    AsyncStudentRepository,
    InMemoryAsyncStudentRepository,
)
from student_manager.services import AsyncStudentService

pytestmark = pytest.mark.integration


def test_cli_creates_report_and_prints_summary(
    csv_writer: CsvWriter,
    config_writer: ConfigWriter,
    capsys: pytest.CaptureFixture[str],
) -> None:
    csv_writer(*STUDENT_ROWS)
    path = config_writer()
    assert main(["--config", str(path)]) == 0
    output = capsys.readouterr().out
    assert "Студентів: 6" in output
    assert "помилок імпорту: 1" in output
    assert "найкращий: Ірина Бондар" in output
    assert (path.parent / "output" / "report.json").exists()


def test_cli_uses_config_yaml_from_current_directory(
    csv_writer: CsvWriter,
    config_writer: ConfigWriter,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    csv_writer(*STUDENT_ROWS[:2])
    config_writer()
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    assert (tmp_path / "output" / "report.json").exists()


def test_environment_variable_redirects_cli_output(
    csv_writer: CsvWriter,
    config_writer: ConfigWriter,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    csv_writer(*STUDENT_ROWS[:2])
    monkeypatch.setenv("STUDENT_MANAGER_OUTPUT_PATH", "custom/result.json")
    assert main(["--config", str(config_writer())]) == 0
    assert (tmp_path / "custom" / "result.json").exists()
    assert not (tmp_path / "output").exists()


def test_cli_in_strict_mode_fails_on_malformed_record(
    csv_writer: CsvWriter,
    config_writer: ConfigWriter,
    capsys: pytest.CaptureFixture[str],
) -> None:
    csv_writer(*STUDENT_ROWS)
    path = config_writer(skip_invalid="false")
    assert main(["--config", str(path)]) == 1
    assert "Помилка: рядок 7" in capsys.readouterr().err
    assert not (path.parent / "output").exists()


def test_cli_reports_output_path_blocked_by_a_file(
    csv_writer: CsvWriter,
    config_writer: ConfigWriter,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    csv_writer(*STUDENT_ROWS[:2])
    (tmp_path / "blocked").write_text(
        "це файл, а не каталог", encoding="utf-8"
    )
    path = config_writer(output_path="blocked/report.json")
    assert main(["--config", str(path)]) == 1
    assert capsys.readouterr().err.startswith("Помилка:")


@pytest.mark.parametrize("setup", ["no-config", "no-csv", "broken-config"])
def test_cli_returns_error_code_for_environment_problems(
    config_writer: ConfigWriter,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    setup: str,
) -> None:
    path = tmp_path / "config.yaml"
    if setup == "no-csv":
        path = config_writer()
    if setup == "broken-config":
        path = config_writer("input_path: [")
    assert main(["--config", str(path)]) == 1
    assert capsys.readouterr().err.startswith("Помилка:")


@pytest.mark.asyncio
async def test_imported_students_are_served_by_async_service(
    csv_writer: CsvWriter,
) -> None:
    students = read_students_csv(csv_writer(*STUDENT_ROWS)).students
    service = AsyncStudentService(InMemoryAsyncStudentRepository(students))
    loaded = await service.load_many([3, 1])
    assert [s.last_name for s in loaded] == ["Бондар", "Коваленко"]
    best = await service.best_student()
    report = build_report(students, pass_threshold=60.0)
    assert best.student_id == report["best_student"]["student_id"] == 3
    with pytest.raises(StudentNotFoundError):
        await service.load(99)


@pytest.mark.asyncio
async def test_async_repository_outage_stops_the_flow_before_the_report(
    csv_writer: CsvWriter,
) -> None:
    students = read_students_csv(csv_writer(*STUDENT_ROWS)).students
    repository = create_autospec(AsyncStudentRepository, instance=True)
    repository.all.side_effect = [students, ConnectionError("розрив")]
    service = AsyncStudentService(repository)
    assert (await service.best_student()).student_id == 3
    with pytest.raises(RepositoryError):
        await service.best_student()
    assert repository.all.await_count == 2


@pytest.mark.asyncio
async def test_async_mock_repository_serves_students_by_id(
    csv_writer: CsvWriter,
) -> None:
    by_id = {
        s.student_id: s
        for s in read_students_csv(csv_writer(*STUDENT_ROWS)).students
    }
    repository = AsyncMock(spec=AsyncStudentRepository)
    repository.get.side_effect = by_id.get
    loaded = await AsyncStudentService(repository).load_many([5, 2])
    assert [s.student_id for s in loaded] == [5, 2]
    assert repository.get.await_args_list[0].args == (5,)
