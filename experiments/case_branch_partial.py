from student_app.grading import classify_grade


def test_excellent() -> None:
    assert classify_grade(95) == "excellent"


def test_unsatisfactory() -> None:
    assert classify_grade(30) == "unsatisfactory"
