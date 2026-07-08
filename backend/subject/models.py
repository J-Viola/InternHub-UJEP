from django.core.validators import MinValueValidator
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
    # min_hours: minimální počet hodin pro splnění praxe v rámci předmětu (task 1.6).
    # Přesun koeficientu z Practice.coefficient dle Ministr 8 + KI_BOP 480h pravidlo.
    # OQ12 (doporučení autora): 480 jako hard default, override per předmět možný.
    # hours_required zůstává pro backward compat (seed data, serializer, admin).
    min_hours = models.IntegerField(
        default=480,
        validators=[MinValueValidator(0)],
        db_index=True,
        help_text="Minimální počet hodin praxe pro splnění předmětu (default 480 dle KI/BOP).",
    )
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
