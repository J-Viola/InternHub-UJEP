from django.urls import path

from .views import StudentPracticeListView

app_name = "student-practices"

urlpatterns = [
    path("student-practices/<int:practice_id>", StudentPracticeListView.as_view(), name="student-practice-list"),
]
