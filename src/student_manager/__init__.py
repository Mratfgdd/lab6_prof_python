"""Система обліку студентів: модель, сервіси, імпорт, експорт і звіти."""

from student_manager.models import Student
from student_manager.services import AsyncStudentService, StudentService

__version__ = "0.6.0"

__all__ = ["AsyncStudentService", "Student", "StudentService", "__version__"]
