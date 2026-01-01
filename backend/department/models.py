from django.db import models


class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(
        unique=True, max_length=100, blank=True, null=True
    )
    department_code = models.CharField(
        unique=True, max_length=100, blank=True, null=True
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "departments"

    def __str__(self):
        return f"{self.department_name} ({self.department_code})"
