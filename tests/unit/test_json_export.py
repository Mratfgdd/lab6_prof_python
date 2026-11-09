import json
from pathlib import Path

import pytest

from student_app import files
from student_app.exceptions import ExportError
from student_app.files import write_json


def test_json_is_written_with_readable_unicode(output_dir: Path) -> None:
    target = output_dir / "report.json"
    write_json(target, {"best": "Коваленко Олена", "average": 91.5})
    text = target.read_text(encoding="utf-8")
    assert "Коваленко Олена" in text
    assert json.loads(text) == {"best": "Коваленко Олена", "average": 91.5}


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

    monkeypatch.setattr(files.json, "dump", broken_dump)
    with pytest.raises(ExportError, match="report.json") as error:
        write_json(target, {"version": 2})
    assert isinstance(error.value.__cause__, OSError)
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 1}


def test_value_that_cannot_be_serialized_raises_export_error(output_dir: Path) -> None:
    with pytest.raises(ExportError) as error:
        write_json(output_dir / "report.json", {"students": {1, 2}})
    assert isinstance(error.value.__cause__, TypeError)
    assert not (output_dir / "report.json").exists()


def test_failure_to_replace_target_raises_export_error(
    output_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def locked(source: object, target: object) -> None:
        raise PermissionError("файл відкрито в іншій програмі")

    monkeypatch.setattr(files.os, "replace", locked)
    with pytest.raises(ExportError):
        write_json(output_dir / "report.json", {})
