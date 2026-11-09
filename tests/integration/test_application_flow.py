import json
from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest
from conftest import ConfigWriter, CsvWriter

from student_app.app import main, run_pipeline
from student_app.config import load_config
from student_app.exceptions import NotificationError
from student_app.services import Notifier

pytestmark = pytest.mark.integration

ROWS = (
    "1,Олена,Коваленко,PI-21,95;92;98",
    "2,Андрій,Мельник,PI-21,78;81;74",
    "3,Ірина,Бондар,PI-22,100;99.5",
    "4,Тарас,Гриценко,PI-22,55;48;62",
    "5,Софія,Гнатюк,PI-23,",
    "6,Дмитро,Бойко,PI-21,abc",
    "7,Катерина,Шевчук,PI-24,90",
)


def test_pipeline_writes_json_report(
    csv_writer: CsvWriter, config_writer: ConfigWriter, output_dir: Path
) -> None:
    csv_writer(*ROWS)
    config = load_config(config_writer(allowed_groups="[PI-21, PI-22, PI-23]"))
    report = run_pipeline(config, create_autospec(Notifier, instance=True))
    saved = json.loads(config.output_path.read_text(encoding="utf-8"))
    assert saved == report
    assert saved["total_students"] == 5
    assert saved["graded_students"] == 4
    assert saved["best_student"]["student_id"] == 3
    assert saved["at_risk"] == [4]
    assert [e["line"] for e in saved["import_errors"]] == [7, 8]
    assert saved["import_errors"][1]["message"] == "група PI-24 не дозволена"


def test_pipeline_sends_one_welcome_message_per_valid_student(
    csv_writer: CsvWriter, config_writer: ConfigWriter
) -> None:
    csv_writer(*ROWS)
    notifier = create_autospec(Notifier, instance=True)
    run_pipeline(load_config(config_writer()), notifier)
    assert notifier.send.call_count == 6
    first_student, first_message = notifier.send.call_args_list[0].args
    assert first_student.student_id == 1
    assert first_message == "Вас зараховано до групи PI-21"


def test_notifier_outage_does_not_stop_the_pipeline(
    csv_writer: CsvWriter, config_writer: ConfigWriter
) -> None:
    csv_writer(*ROWS)
    notifier = MagicMock(spec=Notifier)
    notifier.send.side_effect = NotificationError("сервіс сповіщень недоступний")
    config = load_config(config_writer())
    report = run_pipeline(config, notifier)
    assert report["total_students"] == 6
    assert notifier.send.call_count == 6
    assert config.output_path.exists()


def test_repeated_run_overwrites_report(
    csv_writer: CsvWriter, config_writer: ConfigWriter, output_dir: Path
) -> None:
    csv_writer(*ROWS[:2])
    config = load_config(config_writer())
    run_pipeline(config)
    csv_writer(*ROWS[:4])
    run_pipeline(config)
    assert json.loads(config.output_path.read_text(encoding="utf-8"))["total_students"] == 4


def test_cli_creates_report_and_prints_summary(
    csv_writer: CsvWriter, config_writer: ConfigWriter, capsys: pytest.CaptureFixture[str]
) -> None:
    csv_writer(*ROWS)
    path = config_writer()
    assert main(["--config", str(path)]) == 0
    output = capsys.readouterr().out
    assert "Студентів: 6" in output
    assert "помилок імпорту: 1" in output
    assert "найкращий: Бондар Ірина" in output
    assert (path.parent / "output" / "report.json").exists()


def test_cli_uses_config_yaml_from_current_directory(
    csv_writer: CsvWriter,
    config_writer: ConfigWriter,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    csv_writer(*ROWS[:2])
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
    csv_writer(*ROWS[:2])
    monkeypatch.setenv("STUDENT_APP_OUTPUT_PATH", "custom/result.json")
    assert main(["--config", str(config_writer())]) == 0
    assert (tmp_path / "custom" / "result.json").exists()
    assert not (tmp_path / "output").exists()


def test_cli_in_strict_mode_fails_on_malformed_record(
    csv_writer: CsvWriter, config_writer: ConfigWriter, capsys: pytest.CaptureFixture[str]
) -> None:
    csv_writer(*ROWS)
    path = config_writer(skip_invalid="false")
    assert main(["--config", str(path)]) == 1
    captured = capsys.readouterr()
    assert "Помилка: рядок 7" in captured.err
    assert not (path.parent / "output").exists()


def test_cli_reports_output_path_blocked_by_a_file(
    csv_writer: CsvWriter,
    config_writer: ConfigWriter,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    csv_writer(*ROWS[:2])
    (tmp_path / "blocked").write_text("це файл, а не каталог", encoding="utf-8")
    path = config_writer(output_path="blocked/report.json")
    assert main(["--config", str(path)]) == 1
    assert capsys.readouterr().err.startswith("Помилка:")


@pytest.mark.parametrize(
    "setup",
    ["no-config", "no-csv", "broken-config"],
)
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
