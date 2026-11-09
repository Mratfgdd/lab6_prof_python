import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from student_app.exceptions import ConfigurationError, InvalidGradeError
from student_app.grading import validate_grade
from student_app.models import GROUP_PATTERN, normalize_group

ENV_PREFIX = "STUDENT_APP_"
ENV_NAMES = ("INPUT_PATH", "OUTPUT_PATH", "SKIP_INVALID", "PASS_THRESHOLD")
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class AppConfig:
    input_path: Path
    output_path: Path
    skip_invalid: bool
    pass_threshold: float
    allowed_groups: frozenset[str]


def parse_bool(value: object, name: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ConfigurationError(f"параметр {name} має бути булевим, отримано {value!r}")


def parse_threshold(value: object) -> float:
    try:
        number = float(str(value))
        return validate_grade(number)
    except (ValueError, InvalidGradeError) as error:
        raise ConfigurationError(
            f"pass_threshold має бути числом 0–100, отримано {value!r}"
        ) from error


def parse_groups(value: object) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list) or not value:
        raise ConfigurationError("allowed_groups має бути непорожнім списком")
    groups = frozenset(normalize_group(str(item)) for item in value)
    invalid = sorted(group for group in groups if not GROUP_PATTERN.fullmatch(group))
    if invalid:
        raise ConfigurationError(f"некоректні групи в allowed_groups: {', '.join(invalid)}")
    return groups


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigurationError(f"не вдалося прочитати конфігурацію {path.name}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(f"конфігурація {path.name} не є коректним YAML") from error
    if not isinstance(raw, dict):
        raise ConfigurationError(f"конфігурація {path.name} має бути відображенням ключ-значення")
    return raw


def load_config(path: Path, environ: Mapping[str, str] | None = None) -> AppConfig:
    env = os.environ if environ is None else environ
    raw = read_yaml(path)
    for name in ENV_NAMES:
        if ENV_PREFIX + name in env:
            raw[name.lower()] = env[ENV_PREFIX + name]
    missing = [key for key in ("input_path", "output_path") if raw.get(key) in (None, "")]
    if missing:
        raise ConfigurationError(f"у конфігурації немає ключів: {', '.join(missing)}")
    base = path.parent
    return AppConfig(
        input_path=base / Path(str(raw["input_path"])),
        output_path=base / Path(str(raw["output_path"])),
        skip_invalid=parse_bool(raw.get("skip_invalid", True), "skip_invalid"),
        pass_threshold=parse_threshold(raw.get("pass_threshold", 60)),
        allowed_groups=parse_groups(raw.get("allowed_groups")),
    )
