"""Regression coverage for destructive seed ownership and DB guards."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings

from app.management.commands.seed_demo import SEED_USERNAME_PREFIX, Command
from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice
from subject.models import Subject
from users.models import ApprovalStatus, EmployerProfile, OrganizationUser, ProfessorUser, StudentUser


class DemoSeedOwnershipTests(TestCase):
    def test_reset_only_deletes_seed_marked_accounts(self):
        user_model = get_user_model()
        foreign = user_model.objects.create_user(email="other-origin@test.local", username="external-fixture-user", password="unused")
        demo = user_model.objects.create_user(
            email="demo-account@test.local", username=f"{SEED_USERNAME_PREFIX}demo-student", password="unused"
        )

        Command._reset()

        self.assertTrue(user_model.objects.filter(pk=foreign.pk).exists())
        self.assertFalse(user_model.objects.filter(pk=demo.pk).exists())

    def test_command_reset_preserves_colliding_foreign_practice_and_subject(self):
        department = Department.objects.create(department_name="Seed ownership", department_code="OWN")
        demo_garant = ProfessorUser.objects.create_user(
            email="demo-garant@test.local",
            username=f"{SEED_USERNAME_PREFIX}demo-garant",
            first_name="Demo",
            last_name="Garant",
            is_active=True,
        )
        demo_subject = Subject.objects.create(
            subject_code="DEMO-PRAXE", subject_name="Owned subject", department=department, subject_manager=demo_garant
        )
        foreign_subject = Subject.objects.create(subject_code="FOREIGN-SUBJECT", subject_name="Foreign subject", department=department)

        demo_profile = EmployerProfile.objects.create(company_name="Demo employer", approval_status=ApprovalStatus.APPROVED)
        OrganizationUser.objects.create_user(
            email="demo-org@test.local",
            username=f"{SEED_USERNAME_PREFIX}demo-org",
            first_name="Demo",
            last_name="Org",
            is_active=True,
            employer_profile=demo_profile,
        )
        foreign_profile = EmployerProfile.objects.create(company_name="Foreign employer", approval_status=ApprovalStatus.APPROVED)
        demo_student = StudentUser.objects.create_user(
            email="demo-student@test.local",
            username=f"{SEED_USERNAME_PREFIX}demo-student",
            first_name="Demo",
            last_name="Student",
            is_active=True,
        )
        foreign_student = StudentUser.objects.create_user(
            email="foreign-student@test.local",
            username="foreign-student",
            first_name="Foreign",
            last_name="Student",
            is_active=True,
        )
        demo_practice = Practice.objects.create(
            title="DEMO Kapacita 1",
            employer=demo_profile,
            subject=demo_subject,
            start_date="2027-03-01",
            end_date="2027-06-30",
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        foreign_practice = Practice.objects.create(
            title="DEMO Kapacita 1",
            employer=foreign_profile,
            subject=foreign_subject,
            start_date="2027-03-01",
            end_date="2027-06-30",
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        demo_sp = StudentPractice.objects.create(
            user=demo_student,
            practice=demo_practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date="2027-03-01",
            end_date="2027-06-30",
        )
        foreign_sp = StudentPractice.objects.create(
            user=foreign_student,
            practice=foreign_practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date="2027-03-01",
            end_date="2027-06-30",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = Path(temp_dir) / "spec.json"
            spec_path.write_text(json.dumps({"seed_id": "BL08-SEED-v1"}), encoding="utf-8")
            with (
                mock.patch.object(Command, "_seed", return_value={}),
                mock.patch.object(Command, "_verify_and_report"),
            ):
                call_command("seed_demo", "--spec", str(spec_path), "--reset", "--password", "test-only")

        self.assertFalse(Practice.objects.filter(pk=demo_practice.pk).exists())
        self.assertTrue(Practice.objects.filter(pk=foreign_practice.pk).exists())
        self.assertFalse(StudentPractice.objects.filter(pk=demo_sp.pk).exists())
        self.assertTrue(StudentPractice.objects.filter(pk=foreign_sp.pk).exists())
        self.assertFalse(Subject.objects.filter(pk=demo_subject.pk).exists())
        self.assertTrue(Subject.objects.filter(pk=foreign_subject.pk).exists())

    @override_settings(DEBUG=False, DB_IDENTITY_GUARD=None)
    def test_reset_rejects_non_disposable_db_even_outside_debug(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = Path(temp_dir) / "spec.json"
            spec_path.write_text(json.dumps({"seed_id": "BL08-SEED-v1"}), encoding="utf-8")
            with (
                mock.patch.dict(connection.settings_dict, {"NAME": "internhub_prod"}),
                mock.patch.dict(os.environ, clear=False),  # dev kontejner má BL07_ALLOW_NON_TEST_DB=1
            ):
                os.environ.pop("BL07_ALLOW_NON_TEST_DB", None)
                with self.assertRaises(CommandError):
                    call_command("seed_demo", "--spec", str(spec_path), "--reset")
