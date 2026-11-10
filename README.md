# Student Manager (лабораторна робота №6)

Автоматизоване тестування Python-програм (pytest). Варіант 1 – система обліку
студентів: проєкт `student_manager` з ЛР1 (`Student` з полями `first_name`,
`last_name`, `group`, `average_grade`; функції `calculate_group_average`,
`find_best_student`, `filter_by_group`) доповнений пошуком за ID, репозиторіями
(синхронним і асинхронним), сповіщеннями `Notifier`, CSV import, JSON export,
YAML-конфігурацією зі змінними середовища та async-сервісом.

## Вимоги

Python 3.11+

## Встановлення

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Без встановлення пакета: `python -m pip install -r requirements.txt` і далі
`pytest` з кореня проєкту (`pythonpath = ["src", "tests"]` у `pyproject.toml`).

## Запуск застосунку

```
python -m student_manager.main
student-manager --config config.yaml
```

Змінні середовища перевизначають `config.yaml`: `STUDENT_MANAGER_INPUT_PATH`,
`STUDENT_MANAGER_OUTPUT_PATH`, `STUDENT_MANAGER_SKIP_INVALID`,
`STUDENT_MANAGER_PASS_THRESHOLD`.

## Запуск тестів

Усі тести разом із statement і branch coverage та HTML-звітом (одна команда):

```
pytest -v --cov=student_manager --cov-branch --cov-report=term-missing --cov-report=html
```

Інші корисні команди:

```
pytest
pytest -m "not integration"
pytest -m integration
pytest tests/unit/test_services.py
pytest tests/unit/test_models.py::test_student_is_immutable
```

Поріг покриття – 90 % (`fail_under` у `pyproject.toml`). HTML-звіт створюється
в `htmlcov/index.html`.

## Структура проєкту

```
src/student_manager/
    models.py        Student, classify_grade
    validators.py    перевірка ID, імен, групи й середнього бала 0-100
    services.py      пошук, фільтрація, статистика, StudentService, Notifier
    repositories.py  StudentRepository, AsyncStudentRepository, in-memory
    importers.py     CSV import
    exporters.py     атомарний JSON export
    reports.py       зведений звіт
    config.py        YAML і змінні середовища
    main.py          потік CSV -> звіт, CLI
tests/
    conftest.py      спільні fixtures
    support.py       fake, spy і типи фабрик
    unit/            models, validators, services, repositories, async,
                     configuration, importers, exporters, reports
    integration/     import_pipeline, export_pipeline, application_flow
experiments/         сценарії case_*.py і run_experiments.py (не входять до suite)
report/              генератор PDF-звіту
```

## Експерименти

```
python experiments/run_experiments.py
```

Результати зберігаються в `results/experiments.json`; `results/first_run.txt` –
перший запуск suite (усе зелене, coverage 100 %), `results/negative_run.txt` –
запуск після додавання негативних тестів, які виявили дефекти.

## Звіт

```
python report/build_report.py --venv .venv
```

## Автор

Левандівський Назар
