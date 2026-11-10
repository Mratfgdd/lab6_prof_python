"""Вимірювання для звіту: запуски suite, покриття, збережені запуски."""

import json
import re
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from html_tools import (
    COV_ARGS,
    RESULTS,
    ROOT,
    last_line,
    pytest,
    screenshot,
)

DEFECTS = {
    "plain_decimals": "D1",
    "negative_zero": "D2",
    "non_finite_number": "D3",
    "circular_structure": "D4",
    "non_text_path": "D5",
}

SYMPTOMS = (
    "DID NOT RAISE InvalidGradeError",
    "assert -1.0 == 1.0",
    "DID NOT RAISE ExportError",
    "ValueError: Circular reference detected",
    "DID NOT RAISE ConfigurationError",
)


def total_percent(output: str) -> str:
    """Відсоток покриття з рядка TOTAL у виводі pytest-cov."""
    found = re.search(r"^TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)%", output, re.M)
    assert found, output
    return found.group(1)


@dataclass
class FullRun:
    """Результати повного запуску suite з покриттям."""

    output: str
    total_tests: int
    per_file: Counter[str]
    percent: str
    branches: str
    excluded: int
    index_shot: str


@dataclass
class PartialRuns:
    """Покриття лише unit- та лише integration-тестами."""

    unit_table: str
    unit_percent: str
    integration_percent: str
    unit_summary: str
    integration_summary: str
    missing_file: str
    missing_lines: str
    missing_shot: str


@dataclass
class HistoricRuns:
    """Збережені запуски: перший (зелений) і з негативними тестами."""

    first_excerpt: str
    first_total: int
    negative_lines: str
    failed: int
    errors: int
    passed: int
    mapped: Counter[str]


def measure_full(venv: Path, profile: Path) -> FullRun:
    """Запускає повний suite, збирає HTML coverage і знімок індексу."""
    collected = pytest(venv, "--collect-only", "-q").stdout
    per_file = Counter(
        line.split("::")[0] for line in collected.splitlines() if "::" in line
    )
    cov_json = Path(tempfile.mkdtemp()) / "coverage.json"
    json_run = pytest(venv, "-q", *COV_ARGS, f"--cov-report=json:{cov_json}")
    assert json_run.returncode == 0, json_run.stdout + json_run.stderr
    shutil.rmtree(ROOT / "htmlcov", ignore_errors=True)
    full = pytest(
        venv,
        "-q",
        *COV_ARGS,
        "--cov-report=term-missing",
        "--cov-report=html",
    )
    assert full.returncode == 0, full.stdout + full.stderr
    passed = re.search(r"(\d+) passed", full.stdout)
    assert passed
    assert int(passed.group(1)) == sum(per_file.values())
    assert "failed" not in full.stdout
    row = re.search(
        r"^TOTAL\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", full.stdout, re.M
    )
    assert row
    assert row.group(2) == "0"
    assert row.group(4) == "0"
    excluded = []
    files = json.loads(cov_json.read_text(encoding="utf-8"))["files"]
    for name, entry in files.items():
        lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
        excluded += [lines[i - 1].strip() for i in entry["excluded_lines"]]
    assert all(
        not item or "__main__" in item or item == "sys.exit(main())"
        for item in excluded
    ), excluded
    shot = screenshot(
        ROOT / "htmlcov" / "index.html", 1000, 508, profile, shown=74
    )
    return FullRun(
        output=full.stdout.strip(),
        total_tests=sum(per_file.values()),
        per_file=per_file,
        percent=total_percent(full.stdout),
        branches=row.group(3),
        excluded=len(excluded),
        index_shot=shot,
    )


def measure_partial(venv: Path, profile: Path) -> PartialRuns:
    """Запускає unit-only та integration-only, знімає сторінку main.py."""
    unit_dir = Path(tempfile.mkdtemp()) / "htmlcov_unit"
    unit = pytest(
        venv,
        "-m",
        "not integration",
        *COV_ARGS,
        "--cov-report=term-missing",
        f"--cov-report=html:{unit_dir}",
        "--cov-fail-under=0",
    )
    integration = pytest(
        venv, "-q", "-m", "integration", *COV_ARGS, "--cov-fail-under=0"
    )
    missing = [
        line
        for line in unit.stdout.splitlines()
        if re.search(r"\s\d+%\s+\d", line)
    ]
    assert len(missing) == 1, missing
    assert "main.py" in missing[0], missing
    found = re.match(r"\S*?(\w+\.py)\s.*?%\s+(.*)$", missing[0])
    assert found, missing[0]
    name, lines = found.groups()
    table_lines = [
        line
        for line in unit.stdout.splitlines()
        if line.startswith(("Name", "---", "TOTAL")) or "main.py" in line
    ]
    plain_unit = pytest(venv, "-q", "-m", "not integration")
    shot = screenshot(
        next(unit_dir.glob("*main_py.html")), 1000, 640, profile, shown=80
    )
    return PartialRuns(
        unit_table="\n".join(table_lines),
        unit_percent=total_percent(unit.stdout),
        integration_percent=total_percent(integration.stdout),
        unit_summary=last_line(plain_unit.stdout),
        integration_summary=last_line(integration.stdout),
        missing_file=name,
        missing_lines=lines,
        missing_shot=shot,
    )


def load_historic(total_tests: int) -> HistoricRuns:
    """Читає збережені запуски й зіставляє падіння з дефектами D1-D5."""
    first = (RESULTS / "first_run.txt").read_text(encoding="utf-8")
    negative = (RESULTS / "negative_run.txt").read_text(encoding="utf-8")
    first_passed = re.search(r"(\d+) passed", first)
    assert first_passed
    assert "100%" in first
    summary = re.search(r"(\d+) failed, (\d+) passed, (\d+) error", negative)
    assert summary
    failed_ids = re.findall(r"^FAILED (\S+)", negative, re.M)
    assert int(summary.group(1)) == len(failed_ids)
    assert int(summary.group(2)) + len(failed_ids) == total_tests
    mapped = Counter(
        next(code_ for key, code_ in DEFECTS.items() if key in test_id)
        for test_id in failed_ids
    )
    assert sorted(mapped) == ["D1", "D2", "D3", "D4", "D5"], mapped
    for symptom in SYMPTOMS:
        assert symptom in negative, symptom
    grouped: Counter[str] = Counter()
    for line in negative.splitlines():
        if line.startswith(("FAILED", "ERROR tests")):
            kind, test_id = line.split(" ", 1)
            grouped[f"{kind} {test_id.split(' ')[0].split('[')[0]}"] += 1
    rows = [
        f"{key}  [{count}]" if count > 1 else key
        for key, count in grouped.items()
    ]
    excerpt = [
        line
        for line in first.splitlines()
        if line.startswith(("Name", "TOTAL", "Required"))
    ]
    return HistoricRuns(
        first_excerpt="\n".join([*excerpt, last_line(first)]),
        first_total=int(first_passed.group(1)),
        negative_lines="\n".join([*rows, last_line(negative)]),
        failed=len(failed_ids),
        errors=int(summary.group(3)),
        passed=int(summary.group(2)),
        mapped=mapped,
    )
