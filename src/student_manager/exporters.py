"""Експорт звіту в JSON із атомарним записом файлу."""

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from student_manager.exceptions import ExportError


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Записує JSON через тимчасовий файл і os.replace.

    Якщо запис не вдався, попередній файл залишається недоторканим,
    а тимчасовий файл видаляється.
    """
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(
                payload, file, ensure_ascii=False, indent=2, allow_nan=False
            )
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError) as error:
        temporary.unlink(missing_ok=True)
        raise ExportError(
            f"не вдалося записати {path.name}: {error}"
        ) from error
