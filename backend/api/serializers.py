from department.serializers import DepartmentSerializer
from practices.serializers import PracticeSerializer
from student_practices.serializers import (
    StudentPracticeWithDetailsSerializer as StudentPracticeSerializer,
)
from subject.serializers import SubjectSerializer
from users.serializers import EmployerProfileSerializer

__all__ = [
    "DepartmentSerializer",
    "SubjectSerializer",
    "EmployerProfileSerializer",
    "PracticeSerializer",
    "StudentPracticeSerializer",
]
