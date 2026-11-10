"""Генератор PDF-звіту ЛР6: запускає тести, збирає дані й друкує PDF."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import pymupdf

from html_tools import (
    CSS,
    EDGE,
    PDF_PATH,
    REPORT_DIR,
    RESULTS,
    Numbering,
)
from measurements import load_historic, measure_full, measure_partial
from sections import (
    analysis_section,
    async_and_integration,
    conclusions,
    examples_section,
    experiments_section,
    fixtures_section,
    goal_and_object,
    results_section,
    suite_section,
    title_page,
)


def build_html(venv: Path, profile: Path) -> str:
    """Збирає повний HTML звіту з виміряних даних."""
    n = Numbering()
    full = measure_full(venv, profile)
    partial = measure_partial(venv, profile)
    historic = load_historic(full.total_tests)
    exp = json.loads((RESULTS / "experiments.json").read_text("utf-8"))
    parts = [
        title_page(),
        *goal_and_object(n),
        *suite_section(full, n),
        *fixtures_section(),
        *examples_section(),
        *async_and_integration(),
        *results_section(full, partial, n),
        *analysis_section(full, partial, historic, n),
        *experiments_section(exp, n),
        *conclusions(full),
    ]
    body = "\n".join(parts)
    return (
        "<!doctype html><html lang='uk'><head><meta charset='utf-8'>"
        f"<title>Звіт ЛР6</title><style>{CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


def print_pdf(html_path: Path, pdf_path: Path, profile: Path) -> None:
    """Друкує HTML у PDF через Microsoft Edge."""
    args = [
        str(EDGE),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    subprocess.run(args, check=True, capture_output=True, timeout=120)


def main() -> None:
    """Будує report.html і Звіт_ЛР6_Левандівський.pdf."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path(tempfile.gettempdir()) / "lab6_report_edge_profile",
    )
    args = parser.parse_args()
    html_path = REPORT_DIR / "report.html"
    html_path.write_text(build_html(args.venv, args.profile), encoding="utf-8")
    if PDF_PATH.exists():
        PDF_PATH.unlink()
    print_pdf(html_path, PDF_PATH, args.profile)
    with pymupdf.open(PDF_PATH) as document:
        pages = document.page_count
    print(f"PDF: {PDF_PATH} — {pages} сторінок")


if __name__ == "__main__":
    main()
