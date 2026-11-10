"""Сервіси: функції пошуку/статистики та StudentService із Mock і Fake."""

import logging
from unittest.mock import Mock, call, create_autospec

import pytest
from support import FakeStudentRepository, RecordingNotifier, StudentFactory

from student_manager.exceptions import (
    DuplicateStudentError,
    InvalidGradeError,
    NoStudentsError,
    NotificationError,
    RepositoryError,
    StudentNotFoundError,
)
from student_manager.repositories import (
    InMemoryStudentRepository,
    StudentRepository,
)
from student_manager.services import (
    LoggingNotifier,
    Notifier,
    StudentService,
    calculate_group_average,
    count_by_level,
    filter_by_group,
    find_best_student,
    find_by_id,
    find_by_last_name,
)


def test_filter_by_group_returns_only_members(
    student_factory: StudentFactory,
) -> None:
    first = student_factory(group="PI-21")
    other = student_factory(group="PI-22")
    assert filter_by_group([first, other], "PI-21") == [first]


@pytest.mark.parametrize(
    "group", ["pi-21", " PI-21 "], ids=["lower", "spaces"]
)
def test_filter_by_group_normalizes_group_code(
    student_factory: StudentFactory, group: str
) -> None:
    students = [student_factory(group="PI-21")]
    assert filter_by_group(students, group) == students


def test_filter_by_group_without_members_returns_empty_list(
    student_factory: StudentFactory,
) -> None:
    assert filter_by_group([student_factory()], "PI-99") == []


def test_filter_of_empty_collection_returns_empty_list() -> None:
    assert filter_by_group([], "PI-21") == []


def test_find_by_last_name_ignores_case_and_spaces(
    student_factory: StudentFactory,
) -> None:
    melnyk = student_factory("Мельник")
    students = [student_factory("Бондар"), melnyk]
    assert find_by_last_name(students, "  мЕЛЬНИК ") == [melnyk]


def test_find_by_unknown_last_name_returns_empty_list(
    student_factory: StudentFactory,
) -> None:
    assert find_by_last_name([student_factory()], "Невідомий") == []


def test_find_by_id_returns_student_or_none(
    student_factory: StudentFactory,
) -> None:
    student = student_factory(student_id=5)
    assert find_by_id([student], 5) is student
    assert find_by_id([student], 6) is None
    assert find_by_id([], 5) is None


def test_group_average_is_mean_of_average_grades(
    student_factory: StudentFactory,
) -> None:
    students = [student_factory(average_grade=g) for g in (91.5, 84.0, 88.7)]
    assert calculate_group_average(students) == pytest.approx(88.0666667)


def test_group_average_tolerates_floating_point_noise(
    student_factory: StudentFactory,
) -> None:
    students = [student_factory(average_grade=g) for g in (0.1, 0.2)]
    assert calculate_group_average(students) != 0.15
    assert calculate_group_average(students) == pytest.approx(0.15)


def test_group_average_of_single_student_is_his_grade(
    student_factory: StudentFactory,
) -> None:
    student = student_factory(average_grade=73.0)
    assert calculate_group_average([student]) == pytest.approx(73.0)


def test_group_average_of_empty_collection_raises_custom_error() -> None:
    with pytest.raises(NoStudentsError, match="без студентів"):
        calculate_group_average([])


def test_best_student_has_highest_average_grade(
    student_factory: StudentFactory,
) -> None:
    best = student_factory("Бондар", average_grade=99.5)
    students = [student_factory(average_grade=80.0), best]
    assert find_best_student(students) is best


def test_best_student_tie_prefers_lower_id(
    student_factory: StudentFactory,
) -> None:
    students = [
        student_factory(student_id=8, average_grade=90.0),
        student_factory(student_id=3, average_grade=90.0),
    ]
    assert find_best_student(students).student_id == 3


def test_best_student_of_empty_collection_raises() -> None:
    with pytest.raises(NoStudentsError, match="немає студентів"):
        find_best_student([])


def test_count_by_level_covers_every_level(
    student_factory: StudentFactory,
) -> None:
    students = [student_factory(average_grade=g) for g in (95, 80, 65, 10, 91)]
    assert count_by_level(students) == {
        "excellent": 2,
        "good": 1,
        "satisfactory": 1,
        "unsatisfactory": 1,
    }


def test_register_saves_student_and_notifies_once(
    service: StudentService, notifier: Mock, student_factory: StudentFactory
) -> None:
    student = student_factory(group="PI-22")
    service.register(student)
    assert service.get(student.student_id) is student
    notifier.send.assert_called_once_with(
        student, "Вас зараховано до групи PI-22"
    )


def test_duplicate_registration_raises_and_sends_no_notification(
    service: StudentService, notifier: Mock, student_factory: StudentFactory
) -> None:
    service.register(student_factory(student_id=1))
    notifier.send.reset_mock()
    with pytest.raises(DuplicateStudentError):
        service.register(student_factory(student_id=1))
    notifier.send.assert_not_called()


def test_search_by_id_returns_registered_student(
    populated_service: StudentService,
) -> None:
    assert populated_service.get(3).last_name == "Бондар"


def test_search_by_unknown_id_raises_not_found(
    populated_service: StudentService,
) -> None:
    with pytest.raises(StudentNotFoundError, match="404"):
        populated_service.get(404)


def test_search_by_last_name_is_case_insensitive(
    populated_service: StudentService,
) -> None:
    found = populated_service.find_by_last_name("мельник")
    assert [s.student_id for s in found] == [2]


def test_search_by_unknown_last_name_returns_empty_list(
    populated_service: StudentService,
) -> None:
    assert populated_service.find_by_last_name("Невідомий") == []


def test_students_with_same_last_name_are_sorted_by_id(
    service: StudentService, student_factory: StudentFactory
) -> None:
    service.register(student_factory("Мельник", "Петро", student_id=9))
    service.register(student_factory("Мельник", "Іван", student_id=4))
    found = service.find_by_last_name("Мельник")
    assert [s.student_id for s in found] == [4, 9]


def test_all_students_are_sorted_by_id(
    populated_service: StudentService,
) -> None:
    assert [s.student_id for s in populated_service.all_students()] == [
        1,
        2,
        3,
        4,
        5,
    ]


def test_students_of_group_are_sorted_by_last_name(
    populated_service: StudentService,
) -> None:
    members = populated_service.by_group("pi-21")
    assert [s.last_name for s in members] == ["Коваленко", "Мельник"]


def test_best_student_of_service_has_highest_average_grade(
    populated_service: StudentService,
) -> None:
    best = populated_service.best_student()
    assert best.last_name == "Бондар"
    assert best.average_grade == pytest.approx(99.5)


def test_best_student_of_empty_service_raises(
    service: StudentService,
) -> None:
    with pytest.raises(NoStudentsError):
        service.best_student()


def test_group_average_of_service_is_mean_of_group(
    populated_service: StudentService,
) -> None:
    assert populated_service.group_average("PI-21") == pytest.approx(86.5)
    assert populated_service.group_average("PI-22") == pytest.approx(74.125)


def test_group_average_of_unknown_group_raises(
    populated_service: StudentService,
) -> None:
    with pytest.raises(NoStudentsError, match="PI-99"):
        populated_service.group_average("pi-99")


def test_level_distribution_counts_students_by_level(
    populated_service: StudentService,
) -> None:
    assert populated_service.level_distribution() == {
        "excellent": 2,
        "good": 1,
        "satisfactory": 1,
        "unsatisfactory": 1,
    }


def test_update_above_threshold_changes_grade_without_notification(
    populated_service: StudentService, notifier: Mock
) -> None:
    updated = populated_service.update_average_grade(2, 82.5)
    assert updated.average_grade == pytest.approx(82.5)
    assert populated_service.get(2) == updated
    notifier.send.assert_not_called()


def test_update_below_threshold_notifies_student(
    populated_service: StudentService, notifier: Mock
) -> None:
    updated = populated_service.update_average_grade(5, 41.5)
    notifier.send.assert_called_once_with(
        updated, "Середній бал 41.50 нижчий за 60"
    )


@pytest.mark.parametrize(
    ("grade", "notified"),
    [(60.0, False), (59.99, True)],
    ids=["equals-threshold", "just-below"],
)
def test_notification_threshold_boundary(
    service: StudentService,
    notifier: Mock,
    student_factory: StudentFactory,
    grade: float,
    notified: bool,
) -> None:
    service.register(student_factory(student_id=1))
    notifier.send.reset_mock()
    service.update_average_grade(1, grade)
    assert notifier.send.called is notified


def test_invalid_update_raises_and_keeps_stored_student(
    populated_service: StudentService, notifier: Mock
) -> None:
    before = populated_service.get(1)
    with pytest.raises(InvalidGradeError):
        populated_service.update_average_grade(1, 101)
    assert populated_service.get(1) == before
    notifier.send.assert_not_called()


def test_update_of_unknown_student_raises(service: StudentService) -> None:
    with pytest.raises(StudentNotFoundError):
        service.update_average_grade(77, 90)


def test_invalid_pass_threshold_is_rejected(
    repository: InMemoryStudentRepository, notifier: Mock
) -> None:
    with pytest.raises(InvalidGradeError):
        StudentService(repository, notifier, pass_threshold=101)


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


def test_unexpected_error_from_notifier_is_not_swallowed(
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
    assert not service.failed_notifications


def test_service_reads_student_through_mock_repository(
    student_factory: StudentFactory,
) -> None:
    student = student_factory(student_id=7)
    repository = create_autospec(StudentRepository, instance=True)
    repository.get.return_value = student
    service = StudentService(
        repository, create_autospec(Notifier, instance=True)
    )
    assert service.get(7) is student
    repository.get.assert_called_once_with(7)


def test_mock_repository_returning_none_means_not_found() -> None:
    repository = create_autospec(StudentRepository, instance=True)
    repository.get.return_value = None
    service = StudentService(
        repository, create_autospec(Notifier, instance=True)
    )
    with pytest.raises(StudentNotFoundError):
        service.get(1)


def test_update_touches_repository_exactly_once(
    student_factory: StudentFactory,
) -> None:
    student = student_factory(student_id=1, average_grade=70.0)
    repository = create_autospec(StudentRepository, instance=True)
    repository.get.return_value = student
    service = StudentService(
        repository, create_autospec(Notifier, instance=True)
    )
    service.update_average_grade(1, 90)
    updated = student.with_average_grade(90)
    repository.update.assert_called_once_with(updated)
    assert repository.mock_calls == [call.get(1), call.update(updated)]


def test_fake_repository_and_spy_notifier_allow_state_based_check(
    student_factory: StudentFactory,
) -> None:
    notifier = RecordingNotifier()
    service = StudentService(FakeStudentRepository(), notifier)
    service.register(student_factory(student_id=1, average_grade=50.0))
    service.update_average_grade(1, 40)
    assert notifier.sent == [
        (1, "Вас зараховано до групи PI-21"),
        (1, "Середній бал 40.00 нижчий за 60"),
    ]


def test_logging_notifier_writes_info_record(
    student_factory: StudentFactory, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="student_manager.services"):
        LoggingNotifier().send(student_factory(student_id=3), "Привіт")
    assert "Сповіщення студенту 3: Привіт" in caplog.text
