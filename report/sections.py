"""Розділи звіту: функції повертають фрагменти HTML."""

from typing import Any

from html_tools import (
    FULL_COMMAND,
    MAIN_GUARD,
    TESTS,
    Numbering,
    c,
    code,
    esc,
    extract,
    para,
    plural,
    table,
    terminal,
)
from measurements import FullRun, HistoricRuns, PartialRuns


def title_page() -> str:
    """Титульна сторінка."""
    return """
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
</section>"""


def goal_and_object(n: Numbering) -> list[str]:
    """Мета роботи та опис тестованого проєкту."""
    modules = [
        (
            "models.py",
            f"{c('Student')} (frozen dataclass), {c('classify_grade')}, "
            "4 рівні успішності",
        ),
        (
            "validators.py",
            "перевірка й розбір ID, імен, групи й середнього бала 0–100",
        ),
        (
            "services.py",
            f"{c('filter_by_group')}, {c('find_by_last_name')}, "
            f"{c('calculate_group_average')}, {c('find_best_student')}; "
            f"{c('StudentService')}, {c('AsyncStudentService')}, "
            f"{c('Notifier')} (Protocol)",
        ),
        (
            "repositories.py",
            f"{c('StudentRepository')} і {c('AsyncStudentRepository')} "
            "(Protocol), in-memory реалізації",
        ),
        ("importers.py", "CSV import із валідацією кожного рядка"),
        ("exporters.py", "JSON export через тимчасовий файл (атомарно)"),
        ("reports.py", "зведений звіт: групи, найкращий, рівні, ризик"),
        ("config.py", f"YAML + змінні {c('STUDENT_MANAGER_*')}"),
        ("main.py", "потік CSV → StudentService → JSON, CLI"),
    ]
    return [
        "<h1>Мета роботи</h1>",
        para(
            "Сформувати навички професійного автоматизованого тестування",
            "Python-програм засобами pytest: unit та integration tests,",
            "fixtures, параметризація, перевірка винятків, ізоляція",
            "файлової системи й середовища (tmp_path, monkeypatch), test",
            "doubles (Mock, AsyncMock, fake) та аналіз statement і branch",
            "coverage.",
        ),
        "<h1>1. Об'єкт тестування</h1>",
        para(
            "<b>Варіант 1. Система обліку студентів.</b> Тестується проєкт",
            f"{c('student_manager')} з ЛР1 (студент із полями",
            f"{c('first_name')}, {c('last_name')}, {c('group')},",
            f"{c('average_grade')}; функції {c('calculate_group_average')},",
            f"{c('find_best_student')}, {c('filter_by_group')}), доповнений",
            "пошуком за ID, репозиторіями, сповіщеннями, CSV import,",
            "JSON export, YAML-конфігурацією й async-сервісом.",
            cls="lead",
        ),
        n.tcap("Структура production code (src/student_manager)"),
        table(
            ["Модуль", "Відповідальність"],
            [[c(name), text] for name, text in modules],
        ),
    ]


def matrix_rows() -> list[list[str]]:
    """Рядки test matrix за мінімальною матрицею методички (п. 91)."""
    return [
        [
            "Normal",
            "реєстрація, пошук за ID та прізвищем, фільтр за групою, "
            "середній бал групи, найкращий студент, потік CSV → JSON",
        ],
        [
            "Min boundary",
            "середній бал 0, 0.01 і −0.0 (нормалізується до 0.0); рівень "
            "unsatisfactory для 0; група з одного студента",
        ],
        [
            "Max boundary",
            "середній бал 99.99 і 100; межі рівнів 59.99/60, 74.99/75, "
            "89.99/90; середній бал рівно на порозі сповіщення (60)",
        ],
        [
            "Empty",
            "порожня колекція (<code>NoStudentsError</code>), звіт для "
            "порожньої колекції, CSV лише із заголовком",
        ],
        [
            "Invalid type/value",
            "бал −0.01, 100.01, NaN, ∞, текст, bool; ID 0, −5, bool, "
            "«1»; порожні імена; некоректна група; 12 видів malformed CSV",
        ],
        [
            "Missing data",
            "немає config, ключів input_path/output_path, CSV, колонок; "
            "порожній файл; файл не в UTF-8",
        ],
        [
            "Dependency failure",
            "Notifier → <code>NotificationError</code>, сховище → "
            "<code>RepositoryError</code>, async-сховище → "
            "<code>ConnectionError</code>, <code>json.dump</code> → "
            "<code>OSError</code>, <code>os.replace</code> → "
            "<code>PermissionError</code>",
        ],
        [
            "Repeated operation",
            "повторний student_id (у сховищі й у CSV); повторний запуск "
            "потоку перезаписує звіт",
        ],
        [
            "State transition",
            "невдале оновлення балу не змінює студента й не надсилає "
            "сповіщення; збій сповіщення не скасовує реєстрацію; збій "
            "export не псує попередній файл",
        ],
    ]


def variant_rows() -> list[list[str]]:
    """Відповідність пунктів варіанта 1 файлам тестів."""
    return [
        [
            "створення Student, обов'язкові поля",
            "test_models, test_validators",
        ],
        ["пошук за прізвищем або ID", "test_services, test_repositories"],
        ["фільтрація за групою", "test_services"],
        ["обчислення середнього бала", "test_services"],
        ["найкращий студент", "test_services, test_async_services"],
        ["порожня колекція", "test_services, test_reports"],
        ["boundary та invalid середній бал", "test_validators, test_models"],
        ["CSV import, malformed record", "test_importers"],
        ["JSON export", "test_exporters, test_export_pipeline"],
        ["YAML/configuration", "test_configuration"],
        ["StudentRepository: Mock або fake", "test_services, support.py"],
        ["Notifier: Mock та interaction", "test_services"],
        [
            "збій залежності через side_effect",
            "test_services, test_async_services",
        ],
        [
            "AsyncMock, потік імпорт → звіт",
            "test_async_services, test_application_flow",
        ],
    ]


def suite_section(m: FullRun, n: Numbering) -> list[str]:
    """Структура test suite, відповідність варіанту, test matrix."""
    rows = [
        [c(name.replace("tests/", "").replace("\\", "/")), str(count)]
        for name, count in sorted(m.per_file.items())
    ]
    rows.append(["<b>Разом</b>", f"<b>{m.total_tests}</b>"])
    return [
        "<h1>2. Структура test suite і test matrix</h1>",
        n.tcap("Файли тестів і кількість тестів (з параметризацією)"),
        table(["Файл", "Тестів"], rows),
        para(
            "Спільні fixtures винесено в",
            f"{c('tests/conftest.py')}, fake і spy – у",
            f"{c('tests/support.py')}. Integration tests позначено маркером",
            f"{c('integration')} (зареєстрований у {c('pyproject.toml')},",
            f"{c('--strict-markers')}), тому їх можна запускати окремо.",
        ),
        n.tcap("Відповідність пунктів варіанта 1 файлам тестів"),
        table(["Пункт варіанта 1", "Файли тестів"], variant_rows()),
        n.tcap("Test matrix"),
        table(["Категорія", "Що перевіряється (приклади)"], matrix_rows()),
    ]


def fixtures_section() -> list[str]:
    """Опис і код fixtures."""
    conftest = TESTS / "conftest.py"
    return [
        "<h1>3. Fixtures</h1>",
        para(
            f"Використано autouse ({c('_clean_environment')} прибирає",
            f"змінні {c('STUDENT_MANAGER_*')}), scope=session (незмінний",
            "набір груп), параметризовану fixture",
            f"({c('csv_encoding')}: кодування з BOM і без), fixture",
            f"factory ({c('student_factory')} з лічильником ID),",
            f"{c('Mock(spec=Notifier)')}, ланцюжок fixtures",
            f"({c('service')} → {c('populated_service')}) і fixture із",
            f"yield {c('output_dir')}, яка після тесту перевіряє, що",
            "атомарний export не лишив тимчасових файлів.",
        ),
        code(
            extract(
                conftest,
                "_clean_environment",
                "allowed_groups",
                "csv_encoding",
                "student_factory",
            ),
            keep=True,
        ),
        code(extract(conftest, "notifier", "output_dir"), keep=True),
    ]


def examples_section() -> list[str]:
    """Приклади unit tests: parametrize, raises, approx, Mock, monkeypatch."""
    unit = TESTS / "unit"
    return [
        "<h1>4. Приклади unit tests</h1>",
        para(
            "<b>Parametrization і boundary test:</b> межі рівнів",
            f"оцінювання (з {c('ids')} для читабельного виводу).",
            cls="lead",
        ),
        code(
            extract(unit / "test_models.py", "test_classify_grade_boundaries")
        ),
        para(
            "<b>pytest.raises, custom exception, exc_info і",
            "pytest.approx:</b> середнє порожньої групи піднімає",
            f"{c('NoStudentsError')}; помилка бала знає поле",
            f"({c('field')}); середнє від чисел із плаваючою комою",
            "порівнюється з допуском.",
            cls="lead",
        ),
        code(
            extract(
                unit / "test_services.py",
                "test_group_average_of_empty_collection_raises_custom_error",
                "test_group_average_tolerates_floating_point_noise",
            )
            + "\n\n"
            + extract(
                unit / "test_validators.py",
                "test_invalid_grade_error_names_field_and_offending_value",
            )
        ),
        para(
            "<b>Mock, return_value, interaction assertion:</b>",
            cls="lead",
        ),
        code(
            extract(
                unit / "test_services.py",
                "test_register_saves_student_and_notifies_once",
                "test_service_reads_student_through_mock_repository",
            )
        ),
        para(
            "<b>side_effect і assert_not_called:</b> збій сповіщення не",
            "скасовує реєстрацію, а збій сховища не допускає сповіщення.",
            cls="lead",
        ),
        code(
            extract(
                unit / "test_services.py",
                "test_notifier_failure_does_not_roll_back_registration",
                "test_repository_failure_prevents_notification",
            )
        ),
        para(
            "<b>monkeypatch і tmp_path:</b> змінна середовища",
            f"перевизначає YAML; підміна {c('json')} у модулі експорту",
            "перевіряє, що атомарний export не псує попередній файл.",
            cls="lead",
        ),
        code(
            extract(
                unit / "test_configuration.py",
                "test_environment_variables_override_yaml",
            )
            + "\n\n"
            + extract(
                unit / "test_exporters.py",
                "test_failed_write_keeps_previous_file_and_leaves_no"
                "_temporary_file",
            )
        ),
    ]


def async_and_integration() -> list[str]:
    """AsyncMock та integration tests."""
    unit = TESTS / "unit"
    integ = TESTS / "integration"
    return [
        "<h1>5. AsyncMock</h1>",
        para(
            "Асинхронний репозиторій – зовнішня залежність, тому",
            f"{c('AsyncStudentService')} тестується з",
            f"{c('AsyncMock(spec=AsyncStudentRepository)')}. Перевіряються",
            f"результат, {c('assert_awaited_once_with')},",
            f"{c('assert_not_awaited')} і збій мережі",
            f"({c('side_effect=ConnectionError')}), що стає",
            f"{c('RepositoryError')} зі збереженою причиною. Режим",
            f"pytest-asyncio – {c('strict')}, кожен async-тест має",
            f"{c('@pytest.mark.asyncio')}.",
        ),
        code(
            extract(unit / "test_async_services.py", "async_repository")
            + "\n\n"
            + extract(
                unit / "test_async_services.py",
                "test_load_returns_student_from_async_repository",
                "test_connection_failure_becomes_repository_error_with_cause",
            )
        ),
        "<h1>6. Integration tests</h1>",
        para(
            "Integration tests працюють із реальними файлами в",
            f"{c('tmp_path')} і справжніми компонентами (config → CSV",
            "import → валідація → StudentService → report → JSON export);",
            f"замінено лише зовнішню межу – {c('Notifier')}. Async-тест",
            f"поєднує імпорт із {c('AsyncStudentService')}.",
        ),
        code(
            extract(
                integ / "test_export_pipeline.py",
                "test_pipeline_writes_json_report",
            )
        ),
    ]


def results_section(m: FullRun, p: PartialRuns, n: Numbering) -> list[str]:
    """Результат запуску, coverage, знімок HTML-звіту."""
    run_caption = n.fcap(
        f"Запуск усього suite: {m.total_tests} passed, 0 failed, "
        f"coverage {m.percent} % (statement і branch)"
    )
    index_caption = n.fcap(
        "HTML coverage report (htmlcov/index.html), скриншот Microsoft Edge"
    )
    rows = plural(m.excluded, "рядок", "рядки", "рядків")
    return [
        "<h1>7. Результати запуску та coverage</h1>",
        terminal(FULL_COMMAND, m.output),
        run_caption,
        table(
            ["Набір", "Результат"],
            [
                [
                    '<code>pytest -m "not integration"</code> (unit)',
                    esc(p.unit_summary),
                ],
                [
                    "<code>pytest -m integration</code>",
                    esc(p.integration_summary),
                ],
            ],
        ),
        f'<div class="shot">{m.index_shot}{index_caption}</div>',
        para(
            f"Колонка «excluded» ({rows}) – це блок",
            f"{c(MAIN_GUARD)} (правило",
            f"{c('exclude_also')} у pyproject.toml): виконуваного коду в",
            f"ньому немає. Усі {m.branches} гілок виконано в обох",
            "напрямках (колонка BrPart = 0).",
        ),
    ]


def defect_rows() -> list[list[str]]:
    """Таблиця дефектів production code, знайдених негативними tests."""
    return [
        [
            "D1",
            "<code>parse_average_grade</code> приймає <code>+90</code>, "
            "<code>-0</code>, <code>1e2</code>, <code>9_0</code>, "
            "<code>٩٠</code> (арабсько-індійські цифри), <code>.5</code>, "
            "<code>5.</code> (<code>DID NOT RAISE InvalidGradeError</code>)",
            "розбір через <code>float()</code>, який дозволяє знак, "
            "експоненту, підкреслення й будь-які Unicode-цифри",
            "суворий шаблон <code>[0-9]+(\\.[0-9]+)?</code>",
        ],
        [
            "D2",
            "<code>validate_average_grade(-0.0)</code> повертає "
            "<code>-0.0</code>; у JSON з'явився б «-0.0»",
            "<code>-0.0 >= 0</code> – істина, знак нуля не нормалізовано",
            "<code>return grade + 0.0</code> (−0.0 → 0.0)",
        ],
        [
            "D3",
            "<code>write_json</code> записує <code>NaN</code> і "
            "<code>Infinity</code> – це не валідний JSON "
            "(<code>DID NOT RAISE ExportError</code>)",
            "<code>json.dump</code> за замовчуванням має "
            "<code>allow_nan=True</code>",
            "<code>allow_nan=False</code>, помилка стає "
            "<code>ExportError</code>",
        ],
        [
            "D4",
            "циклічна структура → необроблений <code>ValueError</code>, "
            "а файл <code>report.json.tmp</code> залишається на диску",
            "<code>except</code> ловив лише <code>OSError</code> і "
            "<code>TypeError</code>",
            "<code>ValueError</code> додано до <code>except</code>: "
            "тимчасовий файл видаляється",
        ],
        [
            "D5",
            "<code>input_path: [a.csv]</code>, <code>123</code>, "
            "<code>true</code> приймаються як шлях «['a.csv']», «123» "
            "(<code>DID NOT RAISE ConfigurationError</code>)",
            "значення YAML довільного типу перетворювалось на рядок "
            "через <code>str()</code>",
            "<code>parse_path</code> вимагає рядок, інакше "
            "<code>ConfigurationError</code>",
        ],
    ]


def analysis_section(
    m: FullRun, p: PartialRuns, h: HistoricRuns, n: Numbering
) -> list[str]:
    """Аналіз missing lines та дефекти, знайдені tests."""
    assert h.failed + h.passed == m.total_tests
    added = h.failed + h.passed - h.first_total
    shot_caption = n.fcap(
        f"Сторінка {p.missing_file} у HTML coverage report після запуску "
        "лише unit tests: червоним позначено рядки, яких тести не виконали"
    )
    return [
        "<h1>8. Аналіз недостатньо протестованих paths і дефекти</h1>",
        para(
            "<b>Missing lines.</b> Якщо запустити лише unit tests,",
            f"загальне покриття падає до {p.unit_percent} %. Пропущені",
            "рядки показують, які шляхи перевіряють лише integration tests:",
            cls="lead",
        ),
        terminal(
            'pytest -m "not integration" --cov=student_manager --cov-branch'
            "   # фрагмент: файли без повного покриття і TOTAL",
            p.unit_table,
        ),
        f'<div class="shot">{p.missing_shot}{shot_caption}</div>',
        para(
            f"Рядки {p.missing_lines} у {c(p.missing_file)} – функції",
            f"{c('run_pipeline')} і {c('main')}: їх виконує лише повний",
            "потік (integration tests, CLI). Додавати unit tests немає",
            "потреби. Навпаки, лише integration tests дають",
            f"{p.integration_percent} % і не перевіряють boundary та",
            "invalid-вхід, тому обидва види tests потрібні.",
        ),
        para(
            "<b>Coverage не гарантує відсутність дефектів.</b> Перший",
            f"запуск suite ({h.first_total} tests) дав 100 %",
            "statement і branch coverage й жодного падіння (фрагмент виводу):",
            cls="lead",
        ),
        terminal(
            "pytest -q --cov=student_manager --cov-branch "
            "--cov-report=term-missing   # перший запуск, фрагмент",
            h.first_excerpt,
        ),
        para(
            f"Після цього додано {added} негативні tests на суворий формат",
            "числа, −0.0, NaN/∞ та циклічні структури в export, нетекстові",
            "шляхи в YAML. Покриття лишилось 100 %, але",
            f"{h.failed} tests упали (і {h.errors} error у teardown) –",
            "tests виявили п'ять реальних дефектів production code:",
        ),
        terminal(
            "pytest   # до виправлень; фрагмент short test summary info, "
            "[N] – кількість параметризованих випадків",
            h.negative_lines,
        ),
        n.tcap("Дефекти production code, знайдені tests"),
        table(["№", "Симптом", "Причина", "Виправлення"], defect_rows()),
        para(
            f"Після виправлень усі {m.total_tests} tests проходять, покриття",
            "лишилось 100 %. Висновок: відсоток coverage показує лише",
            "виконаність коду; дефекти знайшли tests із осмисленими",
            "assertions для invalid-входу.",
        ),
    ]


def experiments_section(exp: dict[str, Any], n: Numbering) -> list[str]:
    """Експерименти 1-7 за результатами run_experiments.py."""
    ws = exp["weak_vs_strong"]
    bp, bf = exp["branch_partial"], exp["branch_full"]
    mf, fl, iso = exp["mock_vs_fake"], exp["flaky"], exp["isolation"]
    after = mf["after_refactoring"]
    assert ws["mutant"] == {
        "test_average_weak": "passed",
        "test_average_strong": "failed",
    }
    cover = ws["services_coverage"]
    assert cover["test_average_weak"] == cover["test_average_strong"]
    assert mf["after_refactoring"]["test_get_with_mock_repository"] == "failed"
    assert mf["after_refactoring"]["test_get_with_fake_repository"] == "passed"
    assert fl["failures"]["test_deterministic_student_ids"] == 0
    assert iso["distinct"]
    assert not iso["repository_changed"]
    missing = ", ".join(f"{a}→{b}" for a, b in bp["missing"])
    return [
        "<h1>9. Експерименти</h1>",
        n.tcap(
            "Експерименти 1–2: слабкий і сильний тест на «мутанті» "
            "(середнє замінено на максимум)"
        ),
        table(
            ["Тест", "Код без помилки", "Мутант", "Coverage services.py"],
            [
                [
                    "<code>test_average_weak</code> (без assert)",
                    ws["normal"]["test_average_weak"],
                    ws["mutant"]["test_average_weak"],
                    f"{cover['test_average_weak']} %",
                ],
                [
                    "<code>test_average_strong</code>",
                    ws["normal"]["test_average_strong"],
                    ws["mutant"]["test_average_strong"],
                    f"{cover['test_average_strong']} %",
                ],
            ],
        ),
        para(
            "Обидва тести виконують однакові рядки й дають однаковий",
            "coverage, але помилку ловить лише тест з assert:",
            "execution ≠ verification.",
        ),
        n.tcap("Експерименти 3–7"),
        table(
            ["Експеримент", "Результат"],
            [
                [
                    "3. Branch coverage <code>classify_grade</code>",
                    f"лише excellent і unsatisfactory: {bp['covered']}/"
                    f"{bp['total']} гілок ({bp['percent']} %), пропущено "
                    f"переходи {missing} (рівні good і satisfactory); з усіма "
                    f"чотирма рівнями: {bf['covered']}/{bf['total']} "
                    f"({bf['percent']} %)",
                ],
                [
                    "4. Mock vs fake",
                    "після еквівалентного рефакторингу "
                    "(<code>StudentService.get</code> через "
                    "<code>all_students()</code> замість "
                    "<code>repository.get()</code>): тест з Mock – "
                    f"{after['test_get_with_mock_repository']}"
                    ", з fake – "
                    f"{after['test_get_with_fake_repository']}",
                ],
                [
                    "5. Flaky test",
                    "випадкові ID студентів: "
                    f"{fl['failures']['test_flaky_random_student_ids']} "
                    f"падінь із {fl['runs']} запусків; з фіксованим seed: "
                    f"{fl['failures']['test_deterministic_student_ids']} "
                    f"із {fl['runs']}",
                ],
                [
                    "6. tmp_path isolation",
                    f"{len(iso['tmp_paths'])} запуски – "
                    f"{'різні' if iso['distinct'] else 'ОДНАКОВІ'} "
                    "тимчасові каталоги; змінених файлів у репозиторії: "
                    f"{len(iso['repository_changed'])}",
                ],
                [
                    "7. Failure path",
                    "success і failure залежностей: Notifier "
                    "(<code>return</code> / "
                    "<code>side_effect=NotificationError</code>), сховища "
                    "(<code>RepositoryError</code>, "
                    "<code>ConnectionError</code>), export "
                    "(<code>OSError</code>); перевірено і виняток, і "
                    "відсутність небажаних взаємодій "
                    "(<code>assert_not_called</code>, "
                    "<code>assert_not_awaited</code>)",
                ],
            ],
        ),
        para(
            "Mock перевіряє взаємодію і тому прив'язаний до реалізації –",
            "ламається при рефакторингу без зміни поведінки; fake",
            "перевіряє стан, легше читається й перевикористовується, але",
            "потребує власного коду. Mock доречний на системних межах",
            "(сповіщення, мережа), fake – для сховищ. Flaky-тест",
            "небезпечний тим, що підриває довіру до червоних збірок;",
            "випадковість треба фіксувати (seed, ін'єкція даних).",
        ),
    ]


def conclusions(m: FullRun) -> list[str]:
    """Висновки."""
    return [
        "<h1>Висновки</h1>",
        para(
            f"Створено test suite із {m.total_tests} тестів для системи",
            "обліку студентів (варіант 1): unit tests моделі, валідаторів,",
            "сервісів, репозиторіїв, звітів, конфігурації, CSV import і",
            "JSON export, async-сервісу та integration tests потоку",
            "CSV → валідація → звіт, CLI і async-потоку. Використано fixtures",
            "різних видів, параметризацію, pytest.raises, approx, tmp_path,",
            "monkeypatch, Mock/autospec, AsyncMock і fake. Негативні tests",
            "знайшли п'ять дефектів production code, яких не бачив 100 %",
            f"coverage; statement і branch coverage – {m.percent} % при",
            "порозі 90 % у pyproject.toml. Експерименти показали, що",
            "coverage не замінює змістовних assertions, а",
            "детермінованість та ізоляція тестів важливіші за їх кількість.",
        ),
    ]
