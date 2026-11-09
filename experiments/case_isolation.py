import json
from pathlib import Path

from student_app.files import write_json


def test_export_into_tmp_path(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    write_json(target, {"total_students": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {"total_students": 1}
    print(f"TMP_PATH={tmp_path}")
