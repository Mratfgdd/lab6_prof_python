import logging
from unittest.mock import Mock, call, create_autospec

import pytest
from conftest import StudentFactory
from fakes import FakeStudentRepository, RecordingNotifier

from student_app.exceptions import (
    DuplicateStudentError,
    InvalidGradeError,
    NoStudentsError,
    NotificationError,
    RepositoryError,
    StudentNotFoundError,
)
from student_app.repositories import StudentRepository
from student_app.services import Notifier, StudentService


def test_register_saves_student_and_notifies_once(
    service: StudentService, notifier: Mock, student_factory: StudentFactory
) -> None:
    student = student_factory(group="PI-22")
    service.register(student)
    assert service.get(student.student_id) is student
    notifier.send.assert_called_once_with(student, "Вас зараховано до групи PI-22")


def test_duplicate_registration_raises_and_sends_no_notification(
    service: StudentService, notifier: Mock, student_factory: StudentFactory
) -> None:
    service.register(student_factory(student_id=1))
    notifier.send.reset_mock()
    with pytest.raises(DuplicateStudentError):
        service.register(student_factory(student_id=1))
    notifier.send.assert_not_called()


def test_search_by_id_returns_registered_student(populated_service: StudentService) -> None:
    assert populated_service.get(3).last_name == "Бондар"


def test_search_by_unknown_id_raises_not_found(populated_service: StudentService) -> None:
    with pytest.raises(StudentNotFoundError, match="404"):
        populated_service.get(404)


def test_search_by_last_name_is_case_insensitive(populated_service: StudentService) -> None:
    found = populated_service.find_by_last_name("мельник")
    assert [s.student_id for s in found] == [2]


def test_search_by_unknown_last_name_returns_empty_list(populated_service: StudentService) -> None:
    assert populated_service.find_by_last_name("Невідомий") == []


def test_students_of_same_last_name_are_sorted_by_id(
    service: StudentService, student_factory: StudentFactory
) -> None:
    service.register(student_factory("Мельник", "Петро", student_id=9))
    service.register(student_factory("Мельник", "Іван", student_id=4))
    assert [s.student_id for s in service.find_by_last_name("Мельник")] == [4, 9]


def test_filter_by_group_returns_only_members_sorted_by_name(
    populated_service: StudentService,
) -> None:
    members = populated_service.by_group("PI-21")
    assert [s.last_name for s in members] == ["Коваленко", "Мельник"]


@pytest.mark.parametrize("group", ["pi-21", " PI-21 "], ids=["lowercase", "spaces"])
def test_filter_by_group_normalizes_group_code(
    populated_service: StudentService, group: str
) -> None:
    assert len(populated_service.by_group(group)) == 2


def test_filter_by_group_without_members_returns_empty_list(
    populated_service: StudentService,
) -> None:
    assert populated_service.by_group("PI-99") == []


def test_best_student_has_highest_average(populated_service: StudentService) -> None:
    best = populated_service.best_student()
    assert best.last_name == "Бондар"
    assert best.average == pytest.approx(99.75)


def test_best_student_tie_prefers_lower_id(
    service: StudentService, student_factory: StudentFactory
) -> None:
    service.register(student_factory(student_id=8, grades=(90.0,)))
    service.register(student_factory(student_id=3, grades=(90.0,)))
    assert service.best_student().student_id == 3


def test_best_student_ignores_students_without_grades(
    service: StudentService, student_factory: StudentFactory
) -> None:
    service.register(student_factory(student_id=1, grades=()))
    service.register(student_factory(student_id=2, grades=(40.0,)))
    assert service.best_student().student_id == 2


def test_best_student_of_empty_collection_raises(service: StudentService) -> None:
    with pytest.raises(NoStudentsError, match="немає студентів"):
        service.best_student()


def test_best_student_when_nobody_has_grades_raises(
    service: StudentService, student_factory: StudentFactory
) -> None:
    service.register(student_factory(grades=()))
    with pytest.raises(NoStudentsError):
        service.best_student()


def test_group_average_is_mean_of_student_averages(populated_service: StudentService) -> None:
    assert populated_service.group_average("PI-21") == pytest.approx((95 + 77.6666667) / 2)


def test_group_average_ignores_students_without_grades(populated_service: StudentService) -> None:
    with pytest.raises(NoStudentsError, match="PI-23"):
        populated_service.group_average("PI-23")


def test_level_distribution_counts_students_by_level(populated_service: StudentService) -> None:
    assert populated_service.level_distribution() == {
        "excellent": 2,
        "good": 1,
        "satisfactory": 0,
        "unsatisfactory": 1,
    }


def test_add_grade_updates_average_without_notification_for_good_result(
    populated_service: StudentService, notifier: Mock
) -> None:
    updated = populated_service.add_grade(2, 100)
    assert updated.average == pytest.approx(83.25)
    assert populated_service.get(2) == updated
    notifier.send.assert_not_called()


def test_add_grade_that_leaves_average_below_threshold_notifies_student(
    populated_service: StudentService, notifier: Mock
) -> None:
    updated = populated_service.add_grade(4, 30)
    notifier.send.assert_called_once_with(updated, "Середній бал 48.75 нижчий за 60")


@pytest.mark.parametrize(
    ("grade", "notified"),
    [(60.0, False), (59.99, True)],
    ids=["average-equals-threshold", "average-just-below"],
)
def test_notification_threshold_boundary(
    service: StudentService,
    notifier: Mock,
    student_factory: StudentFactory,
    grade: float,
    notified: bool,
) -> None:
    service.register(student_factory(student_id=1, grades=()))
    notifier.send.reset_mock()
    service.add_grade(1, grade)
    assert notifier.send.called is notified


def test_add_invalid_grade_raises_and_keeps_stored_student(
    populated_service: StudentService, notifier: Mock
) -> None:
    before = populated_service.get(1)
    with pytest.raises(InvalidGradeError):
        populated_service.add_grade(1, 101)
    assert populated_service.get(1) == before
    notifier.send.assert_not_called()


def test_add_grade_to_unknown_student_raises(service: StudentService) -> None:
    with pytest.raises(StudentNotFoundError):
        service.add_grade(77, 90)


def test_notifier_failure_does_not_roll_back_registration(
    service: StudentService,
    notifier: Mock,
    student_factory: StudentFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    notifier.send.side_effect = NotificationError("SMTP недоступний")
    student = student_factory(student_id=6)
    with caplog.at_level(logging.WARNING):
        service.register(student)
    assert service.get(6) is student
    assert service.failed_notifications == [6]
    assert "Не вдалося сповістити студента 6" in caplog.text


def test_non_notification_error_from_notifier_is_not_swallowed(
    service: StudentService, notifier: Mock, student_factory: StudentFactory
) -> None:
    notifier.send.side_effect = RuntimeError("помилка в коді")
    with pytest.raises(RuntimeError):
        service.register(student_factory())


def test_repository_failure_prevents_notification(
    student_factory: StudentFactory,
) -> None:
    repository = create_autospec(StudentRepository, instance=True)
    notifier = create_autospec(Notifier, instance=True)
    repository.add.side_effect = RepositoryError("сховище недоступне")
    service = StudentService(repository, notifier)
    with pytest.raises(RepositoryError):
        service.register(student_factory())
    notifier.send.assert_not_called()
    assert service.failed_notifications == []


def test_service_reads_student_through_mock_repository(student_factory: StudentFactory) -> None:
    student = student_factory(student_id=7)
    repository = create_autospec(StudentRepository, instance=True)
    repository.get.return_value = student
    service = StudentService(repository, create_autospec(Notifier, instance=True))
    assert service.get(7) is student
    repository.get.assert_called_once_with(7)


def test_mock_repository_returning_none_means_not_found() -> None:
    repository = create_autospec(StudentRepository, instance=True)
    repository.get.return_value = None
    service = StudentService(repository, create_autospec(Notifier, instance=True))
    with pytest.raises(StudentNotFoundError):
        service.get(1)


def test_add_grade_updates_repository_exactly_once(student_factory: StudentFactory) -> None:
    student = student_factory(student_id=1, grades=(70.0,))
    repository = create_autospec(StudentRepository, instance=True)
    repository.get.return_value = student
    service = StudentService(repository, create_autospec(Notifier, instance=True))
    service.add_grade(1, 90)
    repository.update.assert_called_once_with(student.with_grade(90))
    assert repository.mock_calls == [call.get(1), call.update(student.with_grade(90))]


def test_fake_repository_and_notifier_allow_state_based_check(
    student_factory: StudentFactory,
) -> None:
    notifier = RecordingNotifier()
    service = StudentService(FakeStudentRepository(), notifier)
    service.register(student_factory(student_id=1, grades=(50.0,)))
    service.add_grade(1, 40)
    assert notifier.sent == [
        (1, "Вас зараховано до групи PI-21"),
        (1, "Середній бал 45.00 нижчий за 60"),
    ]
