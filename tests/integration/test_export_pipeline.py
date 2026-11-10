"""Integration: YAML + CSV -> звіт -> JSON-файл на диску (tmp_path)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from support import STUDENT_ROWS, ConfigWriter, CsvWriter

from student_manager import exporters
from student_manager.config import load_config
from student_manager.exceptions import ExportError, NotificationError
from student_manager.main import run_pipeline
from student_manager.services import Notifier

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("output_dir")
def test_pipeline_writes_json_report(
    csv_writer: CsvWriter, config_writer: ConfigWriter
) -> None:
    csv_writer(*STUDENT_ROWS)
    config = load_config(config_writer(allowed_groups="[PI-21, PI-22, PI-23]"))
    report = run_pipeline(config, Mock(spec=Notifier))
    saved = json.loads(config.output_path.read_text(encoding="utf-8"))
    assert saved == report
    assert saved["total_students"] == 5
    assert saved["best_student"]["student_id"] == 3
    assert saved["at_risk"] == [4]
    assert [e["line"] for e in saved["import_errors"]] == [7, 8]
    assert saved["import_errors"][1]["message"] == "група PI-24 не дозволена"


def test_pipeline_sends_one_welcome_message_per_valid_student(
    csv_writer: CsvWriter, config_writer: ConfigWriter
) -> None:
    csv_writer(*STUDENT_ROWS)
    notifier = Mock(spec=Notifier)
    run_pipeline(load_config(config_writer()), notifier)
    assert notifier.send.call_count == 6
    first_student, first_message = notifier.send.call_args_list[0].args
    assert first_student.student_id == 1
    assert first_message == "Вас зараховано до групи PI-21"


def test_notifier_outage_does_not_stop_the_pipeline(
    csv_writer: CsvWriter, config_writer: ConfigWriter
) -> None:
    csv_writer(*STUDENT_ROWS)
    notifier = MagicMock(spec=Notifier)
    notifier.send.side_effect = NotificationError("сервіс недоступний")
    config = load_config(config_writer())
    report = run_pipeline(config, notifier)
    assert report["total_students"] == 6
    assert notifier.send.call_count == 6
    assert config.output_path.exists()


@pytest.mark.usefixtures("output_dir")
def test_repeated_run_overwrites_report(
    csv_writer: CsvWriter, config_writer: ConfigWriter
) -> None:
    csv_writer(*STUDENT_ROWS[:2])
    config = load_config(config_writer())
    run_pipeline(config)
    csv_writer(*STUDENT_ROWS[:4])
    run_pipeline(config)
    saved = json.loads(config.output_path.read_text(encoding="utf-8"))
    assert saved["total_students"] == 4


@pytest.mark.usefixtures("output_dir")
def test_failed_export_keeps_previous_report_and_leaves_no_temporary_file(
    csv_writer: CsvWriter,
    config_writer: ConfigWriter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_writer(*STUDENT_ROWS[:2])
    config = load_config(config_writer())
    run_pipeline(config)
    before = config.output_path.read_text(encoding="utf-8")

    def locked(source: object, target: object) -> None:
        raise PermissionError("файл відкрито в іншій програмі")

    csv_writer(*STUDENT_ROWS[:4])
    monkeypatch.setattr(exporters, "os", SimpleNamespace(replace=locked))
    with pytest.raises(ExportError):
        run_pipeline(config)
    assert config.output_path.read_text(encoding="utf-8") == before
