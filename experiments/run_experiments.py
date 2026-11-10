"""Запуск експериментів ЛР6 і збереження результатів у results/*.json."""

import importlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RESULTS = ROOT / "results"
IGNORED = {
    ".pytest_cache",
    "__pycache__",
    "htmlcov",
    "results",
    ".ruff_cache",
    ".mypy_cache",
}


def pytest_run(
    *args: str, env: dict[str, str] | None = None
) -> tuple[dict[str, str], str]:
    """Запускає pytest, повертає результати тестів із junit.xml і stdout."""
    with tempfile.TemporaryDirectory() as folder:
        report = Path(folder) / "junit.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={report}",
            *args,
        ]
        done = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={
                **os.environ,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
                **(env or {}),
            },
            check=False,
        )
        outcomes = {}
        for case in ET.parse(report).iter("testcase"):
            failed = (
                case.find("failure") is not None
                or case.find("error") is not None
            )
            outcomes[case.attrib["name"]] = "failed" if failed else "passed"
    return outcomes, done.stdout


def coverage_json(*args: str) -> dict[str, Any]:
    """Запускає pytest із покриттям і повертає coverage.json як словник."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "coverage.json"
        pytest_run(
            *args,
            "--cov=student_manager",
            "--cov-branch",
            f"--cov-report=json:{path}",
            "--cov-fail-under=0",
        )
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def file_entry(data: dict[str, Any], name: str) -> dict[str, Any]:
    """Повертає запис coverage.json для файлу за закінченням шляху."""
    return next(
        v
        for k, v in data["files"].items()
        if k.replace("\\", "/").endswith(name)
    )


def weak_vs_strong() -> dict[str, Any]:
    """Експерименти 1-2: слабкий і сильний тест проти мутанта."""
    target = "experiments/case_weak_strong.py"
    normal, _ = pytest_run(target)
    mutant, _ = pytest_run(target, env={"STUDENT_MUTANT": "1"})
    coverage = {}
    for test in ("test_average_weak", "test_average_strong"):
        entry = file_entry(
            coverage_json(f"{target}::{test}"), "student_manager/services.py"
        )
        coverage[test] = round(entry["summary"]["percent_covered"], 1)
    return {"normal": normal, "mutant": mutant, "services_coverage": coverage}


def branch_stats(test_file: str) -> dict[str, Any]:
    """Експеримент 3: частка покритих гілок classify_grade."""
    models = importlib.import_module("student_manager.models")

    lines, start = inspect.getsourcelines(models.classify_grade)
    end = start + len(lines) - 1
    entry = file_entry(coverage_json(test_file), "student_manager/models.py")

    def inside(arcs: list[list[int]]) -> list[list[int]]:
        return [arc for arc in arcs if start <= arc[0] <= end]

    executed, missing = (
        inside(entry["executed_branches"]),
        inside(entry["missing_branches"]),
    )
    total = len(executed) + len(missing)
    return {
        "covered": len(executed),
        "total": total,
        "percent": round(100 * len(executed) / total, 1),
        "missing": missing,
    }


def mock_vs_fake() -> dict[str, Any]:
    """Експеримент 4: Mock і Fake до та після рефакторингу."""
    target = "experiments/case_mock_vs_fake.py"
    before, _ = pytest_run(target)
    after, _ = pytest_run(target, env={"STUDENT_REFACTORED": "1"})
    return {"before": before, "after_refactoring": after}


def flaky(runs: int = 20) -> dict[str, Any]:
    """Експеримент 5: повторні запуски нестабільного тесту."""
    failures = {
        "test_flaky_random_student_ids": 0,
        "test_deterministic_student_ids": 0,
    }
    for _ in range(runs):
        outcomes, _ = pytest_run("experiments/case_flaky.py")
        for name, outcome in outcomes.items():
            failures[name] += outcome == "failed"
    return {"runs": runs, "failures": failures}


def snapshot() -> set[str]:
    """Множина файлів проєкту без кешів і службових каталогів."""
    files = set()
    for path in ROOT.rglob("*"):
        parts = set(path.relative_to(ROOT).parts)
        if (
            path.is_file()
            and not parts & IGNORED
            and not path.name.startswith(".coverage")
        ):
            files.add(str(path.relative_to(ROOT)))
    return files


def isolation(runs: int = 3) -> dict[str, Any]:
    """Експеримент 6: незалежність tmp_path і чистота репозиторію."""
    before = snapshot()
    paths = []
    for _ in range(runs):
        _, stdout = pytest_run("experiments/case_isolation.py", "-s")
        paths += [
            "/".join(Path(p).parts[-2:])
            for p in re.findall(r"TMP_PATH=(\S+)", stdout)
        ]
    after = snapshot()
    return {
        "tmp_paths": paths,
        "distinct": len(set(paths)) == len(paths) == runs,
        "repository_changed": sorted(after ^ before),
    }


def main() -> None:
    """Виконує всі експерименти й зберігає results/experiments.json."""
    RESULTS.mkdir(exist_ok=True)
    results = {
        "weak_vs_strong": weak_vs_strong(),
        "branch_partial": branch_stats("experiments/case_branch_partial.py"),
        "branch_full": branch_stats("experiments/case_branch_full.py"),
        "mock_vs_fake": mock_vs_fake(),
        "flaky": flaky(),
        "isolation": isolation(),
    }
    (RESULTS / "experiments.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
