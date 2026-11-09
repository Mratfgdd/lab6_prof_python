from student_app.grading import classify_grade


def test_excellent() -> None:
    assert classify_grade(95) == "excellent"


def test_good() -> None:
    assert classify_grade(80) == "good"


def test_satisfactory() -> None:
    assert classify_grade(65) == "satisfactory"


def test_unsatisfactory() -> None:
    assert classify_grade(30) == "unsatisfactory"
