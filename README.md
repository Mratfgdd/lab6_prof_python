# Лабораторна робота №6. Автоматизоване тестування Python-програм

Варіант 1 — «Система обліку студентів». Тестується застосунок `student_app`: модель
`Student` з валідацією, репозиторії (синхронний та асинхронний), сервіси з `Notifier`,
імпорт студентів із CSV, експорт звіту в JSON, конфігурація YAML зі змінними середовища
і CLI-потік CSV → валідація → звіт.

## Встановлення

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Або без встановлення пакета: `python -m pip install -r requirements.txt` і далі `pytest` з кореня
проєкту (`pythonpath = ["src"]` у `pyproject.toml`).

## Запуск

```
pytest
pytest -m "not integration"
pytest -m integration
pytest tests/unit/test_services.py
pytest tests/unit/test_models.py::test_student_is_immutable
pytest --cov=student_app --cov-branch --cov-report=term-missing --cov-report=html
```

`pytest` без аргументів запускає весь набір (195 тестів). Поріг покриття — 90 % (`fail_under` у
`pyproject.toml`). HTML-звіт створюється в `htmlcov/index.html`.

Застосунок:

```
student-report --config config.yaml
```

Змінні середовища перевизначають `config.yaml`: `STUDENT_APP_INPUT_PATH`,
`STUDENT_APP_OUTPUT_PATH`, `STUDENT_APP_SKIP_INVALID`, `STUDENT_APP_PASS_THRESHOLD`.

## Структура

```
src/student_app/   models, grading, repositories, services, reports, files, config, app
tests/
  conftest.py      спільні fixtures
  fakes.py         fake-репозиторій і fake-notifier
  unit/            моделі, оцінювання, репозиторії, сервіси, async, звіти, конфігурація, CSV, JSON
  integration/     імпорт → валідація → звіт, CLI, async-потік
experiments/       демонстраційні сценарії case_*.py (слабкий/сильний тест, branch coverage,
                   Mock vs fake, flaky, tmp_path); не входять до test suite, запускаються
                   лише через run_experiments.py
report/            генератор PDF-звіту
```

## Експерименти

```
python experiments/run_experiments.py
```

Результати зберігаються в `results/experiments.json`; `results/first_run.txt` — вивід
першого запуску тестів, що виявив дефекти в production-коді.

## Звіт

```
python report/build_report.py --venv .venv
```
