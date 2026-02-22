from django.db import models


class Subject(models.Model):
    subject_id = models.AutoField(primary_key=True)
    subject_code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    subject_name = models.CharField(max_length=100, blank=True, default="")
    department = models.ForeignKey(
        "department.Department",
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="subjects",
    )
    hours_required = models.IntegerField(blank=True, null=True)
    subject_manager = models.ForeignKey(
        "users.ProfessorUser",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="managed_subjects",
    )

    class Meta:
        db_table = "subjects"

    def __str__(self):
        return self.subject_name or self.subject_code or super().__str__()
