"""Конфігурація: YAML, змінні середовища (monkeypatch), помилки."""

from pathlib import Path

import pytest
import yaml
from support import ConfigWriter

from student_manager.config import AppConfig, load_config, parse_bool
from student_manager.exceptions import ConfigurationError


def test_config_is_loaded_from_yaml(
    config_writer: ConfigWriter, tmp_path: Path
) -> None:
    path = config_writer(
        allowed_groups="[PI-21, pi-22]", pass_threshold="72.5"
    )
    config = load_config(path)
    assert config == AppConfig(
        input_path=tmp_path / "students.csv",
        output_path=tmp_path / "output" / "report.json",
        skip_invalid=True,
        pass_threshold=72.5,
        allowed_groups=frozenset({"PI-21", "PI-22"}),
    )


def test_optional_parameters_have_defaults(
    config_writer: ConfigWriter,
) -> None:
    path = config_writer("input_path: a.csv\noutput_path: b.json\n")
    config = load_config(path)
    assert config.skip_invalid is True
    assert config.pass_threshold == pytest.approx(60.0)
    assert config.allowed_groups == frozenset()


def test_environment_variables_override_yaml(
    config_writer: ConfigWriter, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = config_writer(pass_threshold="60")
    monkeypatch.setenv("STUDENT_MANAGER_PASS_THRESHOLD", "75")
    monkeypatch.setenv("STUDENT_MANAGER_SKIP_INVALID", "no")
    monkeypatch.setenv("STUDENT_MANAGER_OUTPUT_PATH", "elsewhere/result.json")
    config = load_config(path)
    assert config.pass_threshold == pytest.approx(75.0)
    assert config.skip_invalid is False
    assert config.output_path.name == "result.json"


def test_without_environment_variables_yaml_values_are_used(
    config_writer: ConfigWriter,
) -> None:
    config = load_config(config_writer(pass_threshold="61"))
    assert config.pass_threshold == pytest.approx(61.0)


def test_removed_environment_variable_restores_yaml_value(
    config_writer: ConfigWriter, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = config_writer(pass_threshold="61")
    monkeypatch.setenv("STUDENT_MANAGER_PASS_THRESHOLD", "99")
    monkeypatch.delenv("STUDENT_MANAGER_PASS_THRESHOLD")
    assert load_config(path).pass_threshold == pytest.approx(61.0)


def test_explicit_environment_mapping_replaces_process_environment(
    config_writer: ConfigWriter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STUDENT_MANAGER_PASS_THRESHOLD", "99")
    environ = {"STUDENT_MANAGER_PASS_THRESHOLD": "70"}
    config = load_config(config_writer(), environ=environ)
    assert config.pass_threshold == pytest.approx(70.0)


def test_missing_config_file_raises_configuration_error_with_cause(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigurationError, match="absent.yaml") as error:
        load_config(tmp_path / "absent.yaml")
    assert isinstance(error.value.__cause__, FileNotFoundError)


def test_broken_yaml_keeps_parser_error_as_cause(
    config_writer: ConfigWriter,
) -> None:
    path = config_writer("input_path: [unclosed\noutput_path: {")
    with pytest.raises(ConfigurationError, match="YAML") as error:
        load_config(path)
    assert isinstance(error.value.__cause__, yaml.YAMLError)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("- just\n- a list\n", "відображенням"),
        ("output_path: b.json\n", "input_path"),
        ("input_path: a.csv\n", "output_path"),
        ("input_path: a\noutput_path: b\npass_threshold: 150\n", "0–100"),
        ("input_path: a\noutput_path: b\npass_threshold: -1\n", "0–100"),
        ("input_path: a\noutput_path: b\npass_threshold: high\n", "0–100"),
        ("input_path: a\noutput_path: b\nskip_invalid: maybe\n", "булевим"),
        ("input_path: a\noutput_path: b\nallowed_groups: []\n", "непорожнім"),
        (
            "input_path: a\noutput_path: b\nallowed_groups: [XX]\n",
            "некоректні",
        ),
        (
            "input_path: a\noutput_path: b\nallowed_groups: PI-21\n",
            "непорожнім",
        ),
        ("input_path:\noutput_path: b.json\n", "input_path"),
        ("input_path: a.csv\noutput_path: ''\n", "output_path"),
    ],
    ids=[
        "not-a-mapping",
        "no-input",
        "no-output",
        "threshold-above-max",
        "threshold-negative",
        "threshold-text",
        "skip-invalid-not-bool",
        "groups-empty",
        "groups-bad-code",
        "groups-not-list",
        "input-null",
        "output-empty",
    ],
)
def test_invalid_configuration_raises_configuration_error(
    config_writer: ConfigWriter, text: str, message: str
) -> None:
    with pytest.raises(ConfigurationError, match=message):
        load_config(config_writer(text))


@pytest.mark.parametrize("key", ["input_path", "output_path"])
@pytest.mark.parametrize(
    "value",
    ["[a.csv]", "123", "{a: b}", "true"],
    ids=["list", "int", "map", "bool"],
)
def test_non_text_path_raises_configuration_error(
    config_writer: ConfigWriter, key: str, value: str
) -> None:
    with pytest.raises(ConfigurationError, match=key):
        load_config(config_writer(**{key: value}))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (True, True),
        (False, False),
        ("YES", True),
        (" on ", True),
        ("0", False),
        ("Off", False),
    ],
)
def test_parse_bool_accepts_common_spellings(
    raw: object, expected: bool
) -> None:
    assert parse_bool(raw, "flag") is expected
