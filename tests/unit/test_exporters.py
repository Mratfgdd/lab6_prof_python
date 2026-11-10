"""JSON-експорт: tmp_path, атомарний запис, помилки запису."""

import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from student_manager import exporters
from student_manager.exceptions import ExportError
from student_manager.exporters import write_json


def test_json_is_written_with_readable_unicode(output_dir: Path) -> None:
    target = output_dir / "report.json"
    write_json(target, {"best": "Олена Коваленко", "average": 91.5})
    text = target.read_text(encoding="utf-8")
    assert "Олена Коваленко" in text
    assert json.loads(text) == {"best": "Олена Коваленко", "average": 91.5}


def test_missing_directories_are_created(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "report.json"
    write_json(target, {})
    assert json.loads(target.read_text(encoding="utf-8")) == {}


def test_existing_file_is_replaced(output_dir: Path) -> None:
    target = output_dir / "report.json"
    write_json(target, {"version": 1})
    write_json(target, {"version": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 2}


def test_failed_write_keeps_previous_file_and_leaves_no_temporary_file(
    output_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = output_dir / "report.json"
    write_json(target, {"version": 1})

    def broken_dump(*args: object, **kwargs: object) -> None:
        raise OSError("диск переповнено")

    monkeypatch.setattr(exporters, "json", SimpleNamespace(dump=broken_dump))
    with pytest.raises(ExportError, match="report.json") as error:
        write_json(target, {"version": 2})
    assert isinstance(error.value.__cause__, OSError)
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 1}


def test_value_that_cannot_be_serialized_raises_export_error(
    output_dir: Path,
) -> None:
    target = output_dir / "report.json"
    with pytest.raises(ExportError) as error:
        write_json(target, {"students": {1, 2}})
    assert isinstance(error.value.__cause__, TypeError)
    assert not target.exists()


def test_failure_to_replace_target_raises_export_error(
    output_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def locked(source: object, target: object) -> None:
        raise PermissionError("файл відкрито в іншій програмі")

    monkeypatch.setattr(exporters, "os", SimpleNamespace(replace=locked))
    with pytest.raises(ExportError):
        write_json(output_dir / "report.json", {})


@pytest.mark.parametrize("value", [math.nan, math.inf], ids=["nan", "inf"])
def test_non_finite_number_is_not_exported_as_invalid_json(
    output_dir: Path, value: float
) -> None:
    target = output_dir / "report.json"
    with pytest.raises(ExportError):
        write_json(target, {"average_grade": value})
    assert not target.exists()


def test_circular_structure_raises_export_error_and_keeps_old_file(
    output_dir: Path,
) -> None:
    target = output_dir / "report.json"
    write_json(target, {"version": 1})
    payload: dict[str, Any] = {}
    payload["self"] = payload
    with pytest.raises(ExportError):
        write_json(target, payload)
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 1}
