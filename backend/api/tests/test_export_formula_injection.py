"""Spreadsheet exports must not interpret untrusted text as formulas."""

import csv
import io
from datetime import date

import openpyxl
from django.test import TestCase

from api.export_service import ExportService, _escape_formula_cell
from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice
from subject.models import Subject
from users.models import ApprovalStatus, EmployerProfile, OrganizationRole, OrganizationUser, StudentUser


class ExportFormulaInjectionTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="@subject", subject_code="IT/BOP", department=self.department)
        self.org_user = OrganizationUser.objects.create(email="org@export.test", is_active=True, organization_role=OrganizationRole.OWNER)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.pk,
            company_name="-Company",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()
        self.practice = Practice.objects.create(
            title="+Practice",
            employer=self.employer,
            subject=self.subject,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        self.student = StudentUser.objects.create(
            email="\tstudent@export.test",
            first_name="=cmd|' /C calc'!A0",
            last_name="Normal",
            is_active=True,
        )
        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=4,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today(),
        )
        self.cr_student = StudentUser.objects.create(email="cr@export.test", first_name="\rDanger", last_name="User", is_active=True)
        StudentPractice.objects.create(
            user=self.cr_student,
            practice=self.practice,
            workflow_state=4,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today(),
        )

    def test_csv_escapes_formula_like_text(self):
        content = ExportService.generate_csv(StudentPractice.objects.filter(pk=self.sp.pk))
        rows = list(csv.reader(io.StringIO(content)))
        header = rows[0]
        name = rows[1][header.index("Student")]
        self.assertTrue(name.startswith("'=cmd"))
        self.assertNotIn("\n=cmd", content)
        self.assertNotIn(",=cmd", content)

    def test_xlsx_stores_formula_like_text_as_text(self):
        content = ExportService.generate_xlsx(StudentPractice.objects.filter(pk=self.sp.pk))
        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=False)
        sheet = workbook.active
        cell = sheet.cell(row=2, column=2)
        self.assertTrue(cell.value.startswith("'=cmd"))
        self.assertIn(cell.data_type, ("s", "inlineStr"))

    def test_all_dangerous_prefixes_are_escaped_and_regular_values_are_unchanged(self):
        rows = list(ExportService._export_rows(StudentPractice.objects.all()))
        by_id = {row[0]: row for row in rows}
        headers = [
            "ID prihlasky",
            "Student",
            "Email studenta",
            "Praxe",
            "Organizace",
            "Obor / Predmet",
            "Stav workflow",
            "Datum prihlasky",
            "Od",
            "Do",
            "Dokoncene hodiny",
            "Garant",
        ]
        first = by_id[self.sp.student_practice_id]
        values = dict(zip(headers, first))
        self.assertTrue(values["Student"].startswith("'=cmd"))
        self.assertTrue(values["Email studenta"].startswith("'\t"))
        self.assertTrue(values["Praxe"].startswith("'+"))
        self.assertTrue(values["Organizace"].startswith("'-"))
        self.assertTrue(values["Obor / Predmet"].startswith("'@"))
        self.assertEqual(_escape_formula_cell("\rDanger"), "'\rDanger")
        self.assertEqual(values["Student"].endswith("Normal"), True)
        self.assertEqual(values["ID prihlasky"], self.sp.student_practice_id)
        self.assertEqual(values["Dokoncene hodiny"], 0)
