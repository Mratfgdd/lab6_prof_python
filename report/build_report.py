import argparse
import ast
import base64
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"
RESULTS = ROOT / "results"
PDF_PATH = ROOT / "Звіт_ЛР6_Левандівський.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PROMPT = r"PS C:\Github\prof_python\Lab_06>"

DEFECTS = {
    "blocked_by_a_file": "D5",
    "input-null": "D4",
    "output-empty": "D4",
    "group-none": "D1",
    "group-number": "D1",
    "group-unicode-digits": "D2",
    "grades_that_are_not_a_sequence": "D3",
}


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def code(source: str, keep: bool | None = None) -> str:
    text = source.strip("\n")
    if keep is None:
        keep = text.count("\n") < 18
    return f'<pre class="code{" keep" if keep else ""}">{esc(text)}</pre>'


def extract(path: Path, *names: str) -> str:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    nodes = {
        node.name: node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }
    parts = []
    for name in names:
        node = nodes[name]
        start = min([d.lineno for d in node.decorator_list] + [node.lineno])
        parts.append(textwrap.dedent("\n".join(lines[start - 1 : node.end_lineno])))
    return "\n\n".join(parts)


def terminal(command: str, output: str) -> str:
    return (
        f'<div class="term"><span class="ps">{esc(PROMPT)}</span> {esc(command)}\n'
        f"{esc(output.rstrip())}</div>"
    )


def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


class Numbering:
    def __init__(self) -> None:
        self.table = 0
        self.figure = 0

    def tcap(self, text: str) -> str:
        self.table += 1
        return f'<p class="tcap">Таблиця {self.table} – {text}</p>'

    def fcap(self, text: str) -> str:
        self.figure += 1
        return f'<p class="fcap">Рисунок {self.figure} – {text}</p>'


def pytest(venv: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(venv / "Scripts" / "python.exe"), "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def screenshot(page: Path, width: int, height: int, profile: Path, shown: int = 100) -> str:
    with tempfile.TemporaryDirectory() as folder:
        png = Path(folder) / "shot.png"
        subprocess.run(
            [
                str(EDGE),
                "--headless=new",
                "--disable-gpu",
                f"--user-data-dir={profile}",
                "--hide-scrollbars",
                "--force-device-scale-factor=1.5",
                f"--window-size={width},{height}",
                f"--screenshot={png}",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        data = base64.b64encode(png.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="coverage" style="width: {shown}%">'


CSS = """
@page { size: A4; margin: 20mm 15mm 20mm 30mm;
  @bottom-center { content: counter(page); font: 12pt "Times New Roman", serif; } }
@page :first { @bottom-center { content: none; } }
html { background: #fff; }
body { margin: 0; color: #000; background: #fff; font-family: "Times New Roman", serif;
  font-size: 14pt; line-height: 1.22; }
p { margin: 0 0 2pt; text-indent: 1.25cm; text-align: justify; }
h1 { font-size: 14pt; text-align: center; margin: 9pt 0 4pt; break-after: avoid; }
code { font-family: Consolas, "Courier New", monospace; font-size: 0.8em; }
pre.code { font-family: Consolas, "Courier New", monospace; font-size: 8.1pt;
  line-height: 1.13; margin: 2pt 0 5pt; padding: 3pt 8pt; white-space: pre-wrap;
  background: #f6f6f4; border-left: 3px solid #c3c2b7; orphans: 4; widows: 4; }
pre.keep { break-inside: avoid; }
.term { font-family: Consolas, "Courier New", monospace; font-size: 7.7pt; line-height: 1.15;
  white-space: pre-wrap; background: #0c0c0c; color: #d4d4d4; padding: 4pt 8pt;
  border-radius: 4px; margin: 2pt 0 3pt; break-inside: avoid; }
.term .ps { color: #f9f1a5; }
table { width: 100%; border-collapse: collapse; font-size: 10.5pt; line-height: 1.13;
  margin: 2pt 0 5pt; }
th, td { border: 1px solid #000; padding: 1.5pt 4pt; vertical-align: top; text-align: left; }
th { background: #f0efec; }
tr { break-inside: avoid; }
p.lead { break-after: avoid; }
.tcap { text-indent: 0; text-align: left; margin: 4pt 0 2pt; break-after: avoid; }
.fcap { text-indent: 0; text-align: center; margin: 1pt 0 5pt; }
.shot { break-inside: avoid; text-align: center; margin-top: 3pt; }
.shot img { width: 100%; border: 1px solid #c3c2b7; }
.title { height: 255mm; display: flex; flex-direction: column; justify-content: space-between;
  text-align: center; break-after: page; line-height: 1.5; }
.title .main { margin-top: 30mm; }
.title .main .big { font-size: 20pt; font-weight: bold; letter-spacing: 2pt; }
.title .main .theme { font-size: 16pt; font-weight: bold; margin-top: 10pt; }
.title .sign { align-self: flex-end; text-align: left; width: 85mm; margin-top: 30mm; }
.title .city { margin-top: auto; }
"""


def last_line(text: str) -> str:
    return text.strip().splitlines()[-1]


def build_html(venv: Path, profile: Path) -> str:
    n = Numbering()
    tests = ROOT / "tests"
    unit, integ = tests / "unit", tests / "integration"

    collected = pytest(venv, "--collect-only", "-q").stdout
    per_file = Counter(line.split("::")[0] for line in collected.splitlines() if "::" in line)
    total_tests = sum(per_file.values())
    cov_json = Path(tempfile.mkdtemp()) / "coverage.json"
    json_run = pytest(
        venv, "-q", "--cov=student_app", "--cov-branch", f"--cov-report=json:{cov_json}"
    )
    assert json_run.returncode == 0, json_run.stdout + json_run.stderr
    shutil.rmtree(ROOT / "htmlcov", ignore_errors=True)
    full = pytest(
        venv,
        "-q",
        "--cov=student_app",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-report=html",
    )
    assert full.returncode == 0, full.stdout + full.stderr
    excluded = []
    for name, entry in json.loads(cov_json.read_text(encoding="utf-8"))["files"].items():
        lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
        excluded += [lines[i - 1].strip() for i in entry["excluded_lines"]]
    assert all(
        not ln or ln.endswith("...") or "__main__" in ln or ln == "sys.exit(main())"
        for ln in excluded
    ), excluded
    unit_dir = Path(tempfile.mkdtemp()) / "htmlcov_unit"
    unit_only = pytest(
        venv,
        "-m",
        "not integration",
        "--cov=student_app",
        "--cov-branch",
        "--cov-report=term-missing",
        f"--cov-report=html:{unit_dir}",
        "--cov-fail-under=0",
    )
    integ_only = pytest(
        venv, "-q", "-m", "integration", "--cov=student_app", "--cov-branch", "--cov-fail-under=0"
    )
    integ_total = re.search(r"^TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)%", integ_only.stdout, re.M)
    assert integ_total
    unit_summary = last_line(pytest(venv, "-q", "-m", "not integration").stdout)
    integ_summary = last_line(integ_only.stdout)
    run_output = full.stdout.strip()
    passed = re.search(r"(\d+) passed", full.stdout)
    assert passed
    assert int(passed.group(1)) == total_tests
    assert "failed" not in full.stdout
    total_cov = re.search(r"Total coverage: ([\d.]+)%", full.stdout)
    assert total_cov
    total_row = re.search(r"^TOTAL\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", full.stdout, re.M)
    assert total_row
    assert total_row.group(2) == "0"
    assert total_row.group(4) == "0"
    unit_total = re.search(r"^TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)%", unit_only.stdout, re.M)
    assert unit_total
    unit_missing = [
        line for line in unit_only.stdout.splitlines() if re.search(r"\s\d+%\s+\d", line)
    ]
    assert len(unit_missing) == 2, unit_missing
    assert "app.py" in unit_missing[0], unit_missing
    assert "16-31, 35-49" in unit_missing[0], unit_missing
    assert "services.py" in unit_missing[1], unit_missing
    assert "24, 53" in unit_missing[1], unit_missing
    unit_table = "\n".join(
        line
        for line in unit_only.stdout.splitlines()
        if line.startswith(("Name", "---", "src", "TOTAL"))
    )
    htmlcov = ROOT / "htmlcov"
    shot_index = screenshot(htmlcov / "index.html", 1000, 508, profile, shown=86)
    shot_app = screenshot(next(unit_dir.glob("*app_py.html")), 1000, 760, profile, shown=92)
    exp = json.loads((RESULTS / "experiments.json").read_text(encoding="utf-8"))
    first_run = (RESULTS / "first_run.txt").read_text(encoding="utf-8")
    first_cov = (RESULTS / "first_coverage.txt").read_text(encoding="utf-8")
    failed_ids = re.findall(r"^FAILED (\S+)", first_run, re.M)
    summary = re.search(r"(\d+) failed, (\d+) passed", first_run)
    assert summary
    assert int(summary.group(1)) == len(failed_ids) == 9
    assert int(summary.group(2)) + len(failed_ids) == total_tests
    mapped = Counter(
        next(code_ for key, code_ in DEFECTS.items() if key in test_id) for test_id in failed_ids
    )
    assert sorted(mapped) == ["D1", "D2", "D3", "D4", "D5"], mapped
    for symptom in (
        "'NoneType' object has no attribute 'strip'",
        "DID NOT RAISE ConfigurationError",
        "FileExistsError",
        "'NoneType' object is not iterable",
        "отримано '9'",
    ):
        assert symptom in first_run, symptom
    assert "100%" in first_cov
    assert "186 passed" in first_cov
    short_failures = "\n".join(
        [line for line in first_run.splitlines() if line.startswith("FAILED")]
        + [last_line(first_run)]
    )

    parts: list[str] = []
    add = parts.append
    add("""
<section class="title">
  <div>МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ<br>
  Львівський національний університет імені Івана Франка</div>
  <div class="main">
    <div class="big">ЗВІТ</div>
    <div>до лабораторної роботи №6</div>
    <div>з дисципліни «Професійний Python»</div>
    <div class="theme">Тема: «Автоматизоване тестування Python-програм»</div>
  </div>
  <div class="sign">Виконав:<br>студент Левандівський Назар<br><br>
  Перевірив:<br>Куньо Іван Михайлович</div>
  <div class="city">Львів – 2026</div>
</section>""")

    add("<h1>Мета роботи</h1>")
    add(
        "<p>Сформувати навички професійного автоматизованого тестування Python-програм "
        "засобами pytest: unit та integration tests, fixtures, параметризація, перевірка "
        "винятків, ізоляція файлової системи й середовища (tmp_path, monkeypatch), test "
        "doubles (Mock, AsyncMock, fake) та аналіз statement і branch coverage.</p>"
    )

    add("<h1>1. Об'єкт тестування</h1>")
    add(
        "<p class='lead'><b>Варіант 1. Система обліку студентів.</b> Тестується застосунок "
        "<code>student_app</code>: студент із валідацією обов'язкових полів і списком оцінок, "
        "пошук за ID та прізвищем, фільтрація за групою, середній бал, найкращий студент, "
        "репозиторії (синхронний і асинхронний), сервіс сповіщень <code>Notifier</code>, "
        "CSV import студентів, JSON export звіту, YAML-конфігурація зі змінними середовища та "
        "потік «CSV → валідація → звіт».</p>"
    )
    add(n.tcap("Структура production code (src/student_app)"))
    add(
        table(
            ["Модуль", "Відповідальність"],
            [
                [
                    "<code>models.py</code>",
                    "<code>Student</code> (frozen dataclass): валідація ID, імен, групи й "
                    "оцінок, <code>average</code>, <code>level</code>, <code>with_grade</code>",
                ],
                [
                    "<code>grading.py</code>",
                    "<code>validate_grade</code> (0–100), <code>average_of</code>, "
                    "<code>classify_grade</code> (4 рівні)",
                ],
                [
                    "<code>repositories.py</code>",
                    "<code>StudentRepository</code> і <code>AsyncStudentRepository</code> "
                    "(Protocol), in-memory реалізації",
                ],
                [
                    "<code>services.py</code>",
                    "<code>StudentService</code>, <code>AsyncStudentService</code>, "
                    "<code>Notifier</code> (Protocol): реєстрація, пошук, оцінки, сповіщення",
                ],
                [
                    "<code>reports.py</code>",
                    "найкращий студент, середні по групах, розподіл за рівнями, звіт",
                ],
                [
                    "<code>files.py</code>",
                    "CSV import із валідацією рядків, атомарний JSON export",
                ],
                ["<code>config.py</code>", "YAML + змінні <code>STUDENT_APP_*</code>, перевірка"],
                ["<code>app.py</code>", "потік CSV → StudentService → JSON, CLI"],
            ],
        )
    )

    add("<h1>2. Структура test suite і test matrix</h1>")
    rows = [[f"<code>{esc(name)}</code>", str(count)] for name, count in sorted(per_file.items())]
    rows.append(["<b>Разом</b>", f"<b>{total_tests}</b>"])
    add(n.tcap("Файли тестів і кількість тестів (з урахуванням параметризації)"))
    add(table(["Файл", "Тестів"], rows))
    add(
        "<p>Спільні fixtures винесено в <code>tests/conftest.py</code>, fake-реалізації – у "
        "<code>tests/fakes.py</code>. Integration tests позначено маркером "
        "<code>integration</code> (зареєстрований у <code>pyproject.toml</code>, "
        "<code>--strict-markers</code>), тому їх можна запускати окремо.</p>"
    )
    add(n.tcap("Test matrix"))
    add(
        table(
            ["Категорія", "Що перевіряється (приклади)"],
            [
                [
                    "Normal",
                    "реєстрація, пошук за ID та прізвищем, фільтр за групою, середній бал, "
                    "найкращий студент, потік CSV → JSON",
                ],
                [
                    "Min boundary",
                    "оцінка 0 і 0.01; середній бал 0 → unsatisfactory; один запис оцінок",
                ],
                [
                    "Max boundary",
                    "оцінка 99.99 і 100; межі рівнів 59.99/60, 74.99/75, 89.99/90; середній бал "
                    "рівно на порозі сповіщення (60)",
                ],
                [
                    "Empty",
                    "порожній репозиторій (<code>NoStudentsError</code>), студент без оцінок, "
                    "звіт для порожньої колекції, CSV лише із заголовком",
                ],
                [
                    "Invalid type/value",
                    "оцінки −0.01, 100.01, NaN, ∞, текст, bool; ID 0, −5, bool, «1»; порожні й "
                    "пробільні імена; некоректна група; 11 видів malformed CSV record",
                ],
                [
                    "Missing data",
                    "немає config/ключів input_path, output_path; немає CSV, колонок; порожній "
                    "файл; файл не в UTF-8",
                ],
                [
                    "Dependency failure",
                    "Notifier → <code>NotificationError</code>, сховище → "
                    "<code>RepositoryError</code>, async-сховище → <code>ConnectionError</code>, "
                    "<code>json.dump</code> → <code>OSError</code>, <code>os.replace</code> → "
                    "<code>PermissionError</code>, шлях виводу зайнятий файлом",
                ],
                [
                    "Repeated operation",
                    "повторний student_id (в репозиторії та в CSV); повторний запуск потоку "
                    "перезаписує звіт",
                ],
                [
                    "State transition",
                    "невдале додавання оцінки не змінює студента й не надсилає сповіщення; збій "
                    "сповіщення не скасовує реєстрацію; збій export не псує попередній файл",
                ],
            ],
        )
    )

    add("<h1>3. Fixtures</h1>")
    add(
        "<p>Використано autouse (<code>_clean_environment</code> прибирає змінні "
        "<code>STUDENT_APP_*</code>), scope=session (незмінний набір дозволених груп), fixture "
        "factory (<code>student_factory</code> з лічильником ID), autospec Mock "
        "(<code>notifier</code>), ланцюжок fixtures (<code>service</code> → "
        "<code>populated_service</code>) і fixture із yield <code>output_dir</code>, яка після "
        "тесту перевіряє, що атомарний export не лишив тимчасових файлів.</p>"
    )
    add(
        code(
            extract(
                tests / "conftest.py",
                "_clean_environment",
                "allowed_groups",
                "student_factory",
            ),
            keep=True,
        )
    )
    add(code(extract(tests / "conftest.py", "notifier", "output_dir"), keep=True))

    add("<h1>4. Приклади unit tests</h1>")
    add(
        "<p class='lead'><b>Parametrization і boundary test:</b> межі рівнів оцінювання "
        "(з <code>ids</code> для читабельного виводу).</p>"
    )
    add(code(extract(unit / "test_grading.py", "test_classify_grade_boundaries")))
    add(
        "<p class='lead'><b>pytest.raises, custom exception і pytest.approx:</b> "
        "середній бал без оцінок піднімає <code>EmptyGradesError</code>; середнє від чисел "
        "із плаваючою комою порівнюється з допуском.</p>"
    )
    add(
        code(
            extract(
                unit / "test_models.py",
                "test_average_without_grades_raises_custom_error",
                "test_average_tolerates_floating_point_noise",
            )
        )
    )
    add("<p class='lead'><b>Mock, return_value, interaction assertion:</b></p>")
    add(
        code(
            extract(
                unit / "test_services.py",
                "test_register_saves_student_and_notifies_once",
                "test_service_reads_student_through_mock_repository",
            )
        )
    )
    add(
        "<p class='lead'><b>side_effect і assert_not_called:</b> збій сповіщення не "
        "скасовує реєстрацію, а збій сховища не допускає сповіщення.</p>"
    )
    add(
        code(
            extract(
                unit / "test_services.py",
                "test_notifier_failure_does_not_roll_back_registration",
                "test_repository_failure_prevents_notification",
            )
        )
    )
    add(
        "<p class='lead'><b>monkeypatch і tmp_path:</b> змінна середовища перевизначає "
        "YAML; підміна <code>json.dump</code> перевіряє, що атомарний export не псує "
        "попередній файл.</p>"
    )
    add(
        code(
            extract(unit / "test_configuration.py", "test_environment_variables_override_yaml")
            + "\n\n"
            + extract(
                unit / "test_json_export.py",
                "test_failed_write_keeps_previous_file_and_leaves_no_temporary_file",
            )
        )
    )

    add("<h1>5. AsyncMock</h1>")
    add(
        "<p>Асинхронний репозиторій – зовнішня залежність, тому <code>AsyncStudentService</code> "
        "тестується з <code>create_autospec(AsyncStudentRepository)</code>, який створює "
        "<code>AsyncMock</code> для кожного <code>async def</code>. Перевіряються результат, "
        "<code>assert_awaited_once_with</code>, <code>assert_not_awaited</code> і збій мережі "
        "(<code>side_effect=ConnectionError</code>), що перетворюється на "
        "<code>RepositoryError</code> зі збереженою причиною. Режим pytest-asyncio – "
        "<code>strict</code>.</p>"
    )
    add(
        code(
            extract(unit / "test_async_service.py", "async_repository")
            + "\n\n"
            + extract(
                unit / "test_async_service.py",
                "test_load_returns_student_from_async_repository",
                "test_connection_failure_becomes_repository_error_with_cause",
            )
        )
    )

    add("<h1>6. Integration tests</h1>")
    add(
        "<p>Integration tests працюють із реальними файлами в <code>tmp_path</code> і "
        "справжніми компонентами (config → CSV import → валідація → StudentService → report → "
        "JSON export); замінено лише зовнішню межу – <code>Notifier</code>. Окремий async-тест "
        "поєднує імпорт із <code>AsyncStudentService</code>.</p>"
    )
    add(code(extract(integ / "test_application_flow.py", "test_pipeline_writes_json_report")))

    add("<h1>7. Результати запуску та coverage</h1>")
    add(
        terminal(
            "pytest -q --cov=student_app --cov-branch --cov-report=term-missing --cov-report=html",
            run_output,
        )
    )
    add(
        n.fcap(
            f"Запуск усього suite: {passed.group(1)} passed, 0 failed, coverage "
            f"{total_cov.group(1)} % (statement і branch)"
        )
    )
    add(
        table(
            ["Набір", "Результат"],
            [
                ['<code>pytest -m "not integration"</code> (unit)', esc(unit_summary)],
                ["<code>pytest -m integration</code>", esc(integ_summary)],
            ],
        )
    )
    index_caption = n.fcap("HTML coverage report (htmlcov/index.html), скриншот Microsoft Edge")
    add(f'<div class="shot">{shot_index}{index_caption}</div>')
    add(
        f"<p>Колонка «excluded» ({len(excluded)} рядків) – це блок "
        '<code>if __name__ == "__main__"</code> (правило <code>exclude_also</code> у '
        "pyproject.toml) і методи Protocol-інтерфейсів із тілом <code>...</code>, які "
        "coverage виключає за замовчуванням: виконуваного коду в них немає. Усі "
        f"{total_row.group(3)} гілок виконано в обох напрямках (колонка BrPart = 0).</p>"
    )

    add("<h1>8. Аналіз недостатньо протестованих paths і знайдені дефекти</h1>")
    add(
        "<p class='lead'><b>Missing lines.</b> Якщо запустити лише unit tests, загальне "
        f"покриття падає до {unit_total.group(1)} %. Пропущені рядки показують, які шляхи "
        "перевіряють лише integration tests:</p>"
    )
    add(terminal('pytest -m "not integration" --cov=student_app --cov-branch', unit_table))
    app_caption = n.fcap(
        "Сторінка app.py у HTML coverage report після запуску лише unit tests: червоним "
        "позначено рядки, яких тести не виконали"
    )
    add(f'<div class="shot">{shot_app}{app_caption}</div>')
    add(
        "<p>Рядки 16–31 і 35–49 у <code>app.py</code> – функції <code>run_pipeline</code> і "
        "<code>main</code>; рядок 24 у <code>services.py</code> – "
        "<code>LoggingNotifier.send</code>; рядок 53 – <code>all_students</code>. Усі вони "
        "покриваються integration tests (повний потік, CLI), тож додавати нові unit tests "
        f"немає потреби. Навпаки, лише integration tests дають {integ_total.group(1)} % і не "
        "перевіряють boundary та invalid-вхід, тому обидва види tests потрібні.</p>"
    )
    add(
        "<p class='lead'><b>Coverage не гарантує відсутність дефектів.</b> Перший варіант "
        "suite (186 tests) уже мав 100 % statement і branch coverage:</p>"
    )
    add(
        terminal(
            "pytest --cov=student_app --cov-branch --cov-report=term-missing   # перший запуск",
            first_cov,
        )
    )
    add(
        "<p>Після цього були додані негативні тести на помилкові типи й порожні значення "
        "(9 tests), і вони виявили п'ять реальних дефектів production code:</p>"
    )
    add(terminal("pytest   # після додавання негативних tests, до виправлень", short_failures))
    add(n.tcap("Дефекти production code, знайдені tests"))
    add(
        table(
            ["№", "Симптом", "Причина", "Виправлення"],
            [
                [
                    "D1",
                    "<code>Student(group=None)</code> і <code>group=21</code> → "
                    "<code>AttributeError: 'NoneType' object has no attribute 'strip'</code> "
                    "замість <code>InvalidStudentError</code>",
                    "група нормалізувалась до перевірки типу",
                    "перевірка <code>isinstance(group, str)</code> перед нормалізацією",
                ],
                [
                    "D2",
                    "група <code>PI-٢١</code> (арабсько-індійські цифри) приймається "
                    "(<code>DID NOT RAISE</code>)",
                    "у <code>str</code>-шаблоні <code>\\d</code> збігається з будь-якою "
                    "Unicode-цифрою",
                    "шаблон <code>[A-Z]{2}-[0-9]{2}</code>",
                ],
                [
                    "D3",
                    "<code>grades=None</code> → <code>TypeError: 'NoneType' object is not "
                    'iterable</code>; <code>grades="90"</code> → оцінка «9» і '
                    "<code>InvalidGradeError</code> замість помилки типу",
                    "тип колекції оцінок не перевірявся",
                    "явна перевірка <code>tuple | list</code> → <code>InvalidStudentError</code>",
                ],
                [
                    "D4",
                    "<code>input_path:</code> (null) і <code>output_path: ''</code> "
                    "приймаються (<code>DID NOT RAISE ConfigurationError</code>)",
                    "<code>None</code> перетворювався на шлях «None»",
                    "порожнє значення вважається відсутнім ключем",
                ],
                [
                    "D5",
                    "CLI, якщо каталог виводу зайнятий файлом: необроблений "
                    "<code>FileExistsError</code> замість коду виходу 1",
                    "<code>mkdir</code> виконувався поза блоком <code>try</code>",
                    "<code>mkdir</code> перенесено в <code>try</code>, помилка стає "
                    "<code>ExportError</code>",
                ],
            ],
        )
    )
    add(
        "<p>Після виправлень усі 195 tests проходять, а покриття лишилося 100 %. Висновок: "
        "відсоток coverage показує лише виконаність коду; дефекти знайшли tests із "
        "осмисленими assertions для invalid-входу.</p>"
    )

    add("<h1>9. Експерименти</h1>")
    ws = exp["weak_vs_strong"]
    add(
        n.tcap(
            "Експерименти 1–2: слабкий і сильний тест на «мутанті» (середнє замінено на максимум)"
        )
    )
    add(
        table(
            ["Тест", "Код без помилки", "Мутант", "Coverage models.py"],
            [
                [
                    "<code>test_average_weak</code> (без assert)",
                    ws["normal"]["test_average_weak"],
                    ws["mutant"]["test_average_weak"],
                    f"{ws['models_coverage']['test_average_weak']} %",
                ],
                [
                    "<code>test_average_strong</code>",
                    ws["normal"]["test_average_strong"],
                    ws["mutant"]["test_average_strong"],
                    f"{ws['models_coverage']['test_average_strong']} %",
                ],
            ],
        )
    )
    assert ws["mutant"] == {"test_average_weak": "passed", "test_average_strong": "failed"}
    assert (
        ws["models_coverage"]["test_average_weak"] == ws["models_coverage"]["test_average_strong"]
    )
    add(
        "<p>Обидва тести виконують однакові рядки й дають однаковий coverage, але помилку "
        "ловить лише тест з assert: execution ≠ verification, а coverage показує лише те, що "
        "код виконувався.</p>"
    )
    bp, bf = exp["branch_partial"], exp["branch_full"]
    mf, fl, iso = exp["mock_vs_fake"], exp["flaky"], exp["isolation"]
    add(n.tcap("Експерименти 3–7"))
    add(
        table(
            ["Експеримент", "Результат"],
            [
                [
                    "3. Branch coverage <code>classify_grade</code>",
                    f"лише excellent і unsatisfactory: {bp['covered']}/{bp['total']} гілок "
                    f"({bp['percent']} %), пропущено переходи "
                    + ", ".join(f"{a}→{b}" for a, b in bp["missing"])
                    + f" (рівні good і satisfactory); з усіма чотирма рівнями: "
                    f"{bf['covered']}/{bf['total']} ({bf['percent']} %)",
                ],
                [
                    "4. Mock vs fake",
                    "після еквівалентного рефакторингу (<code>StudentService.get</code> через "
                    "<code>repository.all()</code> замість <code>repository.get()</code>): тест "
                    f"з Mock – {mf['after_refactoring']['test_get_with_mock_repository']}, з "
                    f"fake – {mf['after_refactoring']['test_get_with_fake_repository']}",
                ],
                [
                    "5. Flaky test",
                    "випадкові ID студентів: "
                    f"{fl['failures']['test_flaky_random_student_ids']} падінь із {fl['runs']} "
                    "запусків; з фіксованим seed: "
                    f"{fl['failures']['test_deterministic_student_ids']} із {fl['runs']}",
                ],
                [
                    "6. tmp_path isolation",
                    f"{len(iso['tmp_paths'])} запуски – "
                    f"{'різні' if iso['distinct'] else 'ОДНАКОВІ'} тимчасові каталоги; змінених "
                    f"файлів у репозиторії: {len(iso['repository_changed'])}",
                ],
                [
                    "7. Failure path",
                    "success і failure залежностей: Notifier (<code>return</code> / "
                    "<code>side_effect=NotificationError</code>), сховища "
                    "(<code>RepositoryError</code>, <code>ConnectionError</code>), export "
                    "(<code>OSError</code>); перевірено і виняток, і відсутність небажаних "
                    "взаємодій (<code>assert_not_called</code>, "
                    "<code>assert_not_awaited</code>)",
                ],
            ],
        )
    )
    add(
        "<p>Mock перевіряє взаємодію і тому прив'язаний до реалізації – ламається при "
        "рефакторингу без зміни поведінки; fake перевіряє стан, легше читається й "
        "перевикористовується, але потребує власного коду. Mock доречний на системних межах "
        "(сповіщення, мережа), fake – для сховищ. Flaky-тест небезпечний тим, що підриває "
        "довіру до червоних збірок; випадковість треба фіксувати (seed, ін'єкція даних).</p>"
    )
    assert mf["after_refactoring"]["test_get_with_mock_repository"] == "failed"
    assert mf["after_refactoring"]["test_get_with_fake_repository"] == "passed"
    assert fl["failures"]["test_deterministic_student_ids"] == 0
    assert iso["distinct"]
    assert not iso["repository_changed"]

    add("<h1>Висновки</h1>")
    add(
        f"<p>Створено test suite із {total_tests} тестів для системи обліку студентів "
        "(варіант 1): unit tests моделі, оцінювання, репозиторіїв, сервісів, звітів, "
        "конфігурації, CSV import і JSON export, async-сервісу та integration tests повного "
        "потоку CSV → валідація → звіт, CLI і async-потоку. Використано fixtures різних "
        "видів, параметризацію, pytest.raises, approx, tmp_path, monkeypatch, "
        "Mock/autospec, AsyncMock і fake. Негативні тести знайшли п'ять дефектів production "
        "code, які не бачив 100 % coverage; statement і branch coverage – "
        f"{total_cov.group(1)} % при порозі 90 % у pyproject.toml. Експерименти показали, що "
        "coverage не замінює змістовних assertions, а детермінованість та ізоляція тестів "
        "важливіші за їх кількість.</p>"
    )

    body = "\n".join(parts)
    return (
        "<!doctype html><html lang='uk'><head><meta charset='utf-8'>"
        f"<title>Звіт ЛР6</title><style>{CSS}</style></head><body>{body}</body></html>"
    )


def print_pdf(html_path: Path, pdf_path: Path, profile: Path) -> None:
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

    import pymupdf

    with pymupdf.open(PDF_PATH) as document:
        print(f"PDF: {PDF_PATH} — {document.page_count} сторінок")


if __name__ == "__main__":
    main()
