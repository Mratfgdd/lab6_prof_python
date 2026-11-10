"""CSV-імпорт: коректні файли, malformed-рядки, strict-режим, кодування."""

from pathlib import Path

import pytest
from support import CsvWriter

from student_manager.exceptions import ImportDataError
from student_manager.importers import read_students_csv

VALID = "1,Олена,Коваленко,PI-21,95.5"


def test_valid_file_is_converted_to_students(csv_writer: CsvWriter) -> None:
    path = csv_writer(VALID, "2,Андрій,Мельник,PI-22,70.25")
    result = read_students_csv(path)
    assert [s.last_name for s in result.students] == ["Коваленко", "Мельник"]
    assert result.students[1].average_grade == pytest.approx(70.25)
    assert not result.issues


def test_file_with_header_only_gives_empty_collection(
    csv_writer: CsvWriter,
) -> None:
    result = read_students_csv(csv_writer())
    assert not result.students
    assert not result.issues


def test_both_encodings_are_supported(
    csv_writer: CsvWriter, csv_encoding: str
) -> None:
    path = csv_writer(VALID, encoding=csv_encoding)
    students = read_students_csv(path).students
    assert [s.first_name for s in students] == ["Олена"]


@pytest.mark.parametrize(
    ("grade", "expected"),
    [("0", 0.0), ("100", 100.0), ("59.99", 59.99)],
    ids=["minimum", "maximum", "fraction"],
)
def test_boundary_average_grades_are_imported(
    csv_writer: CsvWriter, grade: str, expected: float
) -> None:
    path = csv_writer(f"5,Анна,Коваль,PI-21,{grade}")
    students = read_students_csv(path).students
    assert students[0].average_grade == pytest.approx(expected)


@pytest.mark.parametrize(
    ("row", "fragment"),
    [
        ("abc,Анна,Коваль,PI-21,90", "student_id має бути цілим"),
        ("0,Анна,Коваль,PI-21,90", "додатним"),
        ("5,,Коваль,PI-21,90", "first_name"),
        ("5,Анна,   ,PI-21,90", "last_name"),
        ("5,Анна,Коваль,XX-1,90", "некоректна група"),
        ("5,Анна,Коваль,PI-21,101", "поза діапазоном"),
        ("5,Анна,Коваль,PI-21,-1", "десятковим числом"),
        ("5,Анна,Коваль,PI-21,9o", "десятковим числом"),
        ("5,Анна,Коваль,PI-21,nan", "десятковим числом"),
        ("5,Анна,Коваль,PI-21,", "десятковим числом"),
        ("5,Анна,Коваль,PI-21", "відсутні поля: average_grade"),
        ("5,Анна,Коваль,PI-21,90,зайве", "зайві поля"),
    ],
    ids=[
        "id-not-number",
        "id-zero",
        "first-name-empty",
        "last-name-blank",
        "group-bad-format",
        "grade-above-max",
        "grade-negative",
        "grade-typo",
        "grade-nan",
        "grade-empty",
        "missing-field",
        "extra-field",
    ],
)
def test_malformed_record_is_reported_and_skipped(
    csv_writer: CsvWriter, row: str, fragment: str
) -> None:
    result = read_students_csv(csv_writer(VALID, row))
    assert [s.student_id for s in result.students] == [1]
    assert len(result.issues) == 1
    assert result.issues[0].line_number == 3
    assert fragment in result.issues[0].message


def test_strict_mode_stops_on_first_malformed_record(
    csv_writer: CsvWriter,
) -> None:
    path = csv_writer(VALID, "x,Анна,Коваль,PI-21,90", "y,Ще,Одна,PI-21,90")
    with pytest.raises(ImportDataError, match="рядок 3") as error:
        read_students_csv(path, skip_invalid=False)
    assert error.value.line_number == 3
    assert isinstance(error.value.__cause__, ValueError)


def test_duplicate_student_id_is_reported(csv_writer: CsvWriter) -> None:
    result = read_students_csv(csv_writer(VALID, "1,Інший,Студент,PI-22,50"))
    assert len(result.students) == 1
    assert result.issues[0].message == "дублікат student_id 1"


def test_group_outside_allowed_list_is_rejected(csv_writer: CsvWriter) -> None:
    path = csv_writer(VALID, "2,Анна,Коваль,PI-24,90")
    allowed = frozenset({"pi-21", "PI-22"})
    result = read_students_csv(path, allowed_groups=allowed)
    assert [s.student_id for s in result.students] == [1]
    assert result.issues[0].message == "група PI-24 не дозволена"


def test_missing_columns_fail_even_in_tolerant_mode(
    csv_writer: CsvWriter,
) -> None:
    path = csv_writer(
        "1,Олена,Коваленко", header="student_id,first_name,last_name"
    )
    with pytest.raises(ImportDataError, match="group, average_grade"):
        read_students_csv(path)


def test_empty_file_raises_import_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_bytes(b"")
    with pytest.raises(ImportDataError, match="немає колонок"):
        read_students_csv(path)


def test_missing_file_raises_import_error_with_cause(tmp_path: Path) -> None:
    with pytest.raises(ImportDataError, match="absent.csv") as error:
        read_students_csv(tmp_path / "absent.csv")
    assert isinstance(error.value.__cause__, FileNotFoundError)


def test_file_in_wrong_encoding_raises_import_error(tmp_path: Path) -> None:
    path = tmp_path / "cp1251.csv"
    path.write_bytes("student_id,first_name\n1,Олена\n".encode("cp1251"))
    with pytest.raises(ImportDataError) as error:
        read_students_csv(path)
    assert isinstance(error.value.__cause__, UnicodeDecodeError)
