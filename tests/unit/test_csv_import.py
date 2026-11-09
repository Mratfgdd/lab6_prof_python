from pathlib import Path

import pytest
from conftest import CsvWriter

from student_app.exceptions import ImportDataError
from student_app.files import parse_grades, read_students_csv

VALID = "1,Олена,Коваленко,PI-21,95;90"


def test_valid_file_is_converted_to_students(csv_writer: CsvWriter) -> None:
    path = csv_writer(VALID, "2,Андрій,Мельник,PI-22,70.5;71.5;72")
    result = read_students_csv(path)
    assert [s.last_name for s in result.students] == ["Коваленко", "Мельник"]
    assert result.students[1].average == pytest.approx(71.3333333)
    assert result.issues == []


def test_file_with_header_only_gives_empty_collection(csv_writer: CsvWriter) -> None:
    result = read_students_csv(csv_writer())
    assert result.students == []
    assert result.issues == []


def test_student_without_grades_is_valid(csv_writer: CsvWriter) -> None:
    result = read_students_csv(csv_writer("3,Софія,Гнатюк,PI-23,"))
    assert result.students[0].grades == ()


def test_file_with_byte_order_mark_is_supported(tmp_path: Path) -> None:
    path = tmp_path / "bom.csv"
    path.write_text(
        "student_id,first_name,last_name,group,grades\n" + VALID + "\n", encoding="utf-8-sig"
    )
    assert len(read_students_csv(path).students) == 1


@pytest.mark.parametrize(
    ("row", "fragment"),
    [
        ("abc,Анна,Коваль,PI-21,90", "некоректне число"),
        ("0,Анна,Коваль,PI-21,90", "некоректний студент"),
        ("5,,Коваль,PI-21,90", "first_name"),
        ("5,Анна,   ,PI-21,90", "last_name"),
        ("5,Анна,Коваль,XX-1,90", "некоректна група"),
        ("5,Анна,Коваль,PI-21,101", "некоректна оцінка"),
        ("5,Анна,Коваль,PI-21,-1", "некоректна оцінка"),
        ("5,Анна,Коваль,PI-21,9o", "некоректне число"),
        ("5,Анна,Коваль,PI-21,nan", "некоректна оцінка"),
        ("5,Анна,Коваль,PI-21", "відсутні поля: grades"),
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


def test_strict_mode_stops_on_first_malformed_record(csv_writer: CsvWriter) -> None:
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
    result = read_students_csv(path, allowed_groups=frozenset({"pi-21", "PI-22"}))
    assert [s.student_id for s in result.students] == [1]
    assert result.issues[0].message == "група PI-24 не дозволена"


def test_missing_columns_fail_even_in_tolerant_mode(csv_writer: CsvWriter) -> None:
    path = csv_writer("1,Олена,Коваленко", header="student_id,first_name,last_name")
    with pytest.raises(ImportDataError, match="group, grades"):
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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("90;85", (90.0, 85.0)),
        (" 90 ; ;85 ", (90.0, 85.0)),
        ("", ()),
        (";;", ()),
        ("100", (100.0,)),
    ],
    ids=["two-grades", "spaces-and-gaps", "empty", "only-separators", "single"],
)
def test_parse_grades(raw: str, expected: tuple[float, ...]) -> None:
    assert parse_grades(raw) == expected
