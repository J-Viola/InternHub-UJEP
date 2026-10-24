"""BL-02 — authorization / data-integrity regression tests (audit 2026-10-04).

Defect areas covered (exact endpoint + payload + actor + HTTP status + persisted DB before/after):

- BE-001 / REQ-011 (alias, one fix): POST /api/student-practices/{id}/confirm-contract/
  cizí aktér nesmí změnit approval flagy ani stav; oprávněný vlastník nesmí být blokován.
  T1 (vlastník, 2026-10-09, bl01-decisions.md): aktér zapíše jen svou vlastní osu;
  CONTRACTED + approval_status=APPROVED jen při obou osách (touto akcí nebo již dříve);
  owner-student = receipt only; kapacita počítá jen CONTRACTED.
- BE-002: GET/PATCH/DELETE/POST /api/student-practices/evaluations/{...} — žádné cizí
  čtení ani mutace evaluací; vlastník oprávněně pracuje.
- BE-015: POST /api/student-practices/{id}/transition/ — cizí studentský opravný
  přechod odmítnut bez mutace; vlastník si opravný přechod zachová (hrany C19
  se nemění).

Vše syntetické; běh izolovanými test settings (viz audit COMMANDS.md).
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from notifications.models import Notification
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import (
    DocumentStatus,
    DocumentType,
    Evaluation,
    StudentPractice,
    StudentPracticeWorkflowState,
    UploadedDocument,
)
from subject.models import Subject
from users.models import (
    ActionLog,
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class BL02FixtureMixin:
    """Sdílená syntetická fixture: dva studenti, dvě katedry, dvě organizace, garanti."""

    def setUp(self):
        self.client = APIClient()

        self.department = Department.objects.create(department_name="BL02 KI", department_code="BKI")
        self.other_department = Department.objects.create(department_name="BL02 MA", department_code="BMA")
        self.subject = Subject.objects.create(
            subject_name="BL02 praxe",
            subject_code="BL02/BOP",
            department=self.department,
            min_hours=480,
        )

        # Zaměstnavatel praxe (oprávněná organizace)
        self.org_user = OrganizationUser.objects.create(
            email="owner-org@bl02.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.pk,
            company_name="BL02 Org",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        # Cizí organizace (jiný employer)
        self.foreign_org = OrganizationUser.objects.create(
            email="foreign-org@bl02.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.foreign_employer = EmployerProfile.objects.create(
            employer_id=self.foreign_org.pk,
            company_name="BL02 Foreign Org",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.foreign_org.employer_profile = self.foreign_employer
        self.foreign_org.save()

        # Studenti: vlastník cílových SP a cizí student
        self.student_owner = StudentUser.objects.create(
            email="owner-student@bl02.test",
            first_name="BL02",
            last_name="Owner",
            is_active=True,
        )
        self.foreign_student = StudentUser.objects.create(
            email="foreign-student@bl02.test",
            first_name="BL02",
            last_name="Foreign",
            is_active=True,
        )

        # Pedagogové: garant/HEAD správné katedry a cizí HEAD jiné katedry
        self.garant = ProfessorUser.objects.create_user(
            email="garant@bl02.test",
            password="bl02-only-password",
            first_name="BL02",
            last_name="Garant",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        self.foreign_professor = ProfessorUser.objects.create_user(
            email="foreign-prof@bl02.test",
            password="bl02-only-password",
            first_name="BL02",
            last_name="ForeignProf",
            is_active=True,
            department=self.other_department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@bl02.test",
            password="bl02-only-password",
        )

        self.subject.subject_manager_id = self.garant.pk
        self.subject.save(update_fields=["subject_manager"])

        self.practice = Practice.objects.create(
            title="BL02 praxe",
            description="Syntetická praxe pro BL02 testy",
            employer=self.employer,
            subject=self.subject,
            contact_user=self.org_user,  # in-app příjemce ALLOCATION_ORG (T1 side-effect test)
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=40),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            available_positions=10,
        )

    def make_sp(self, user, *, practice=None, state=StudentPracticeWorkflowState.APPLIED, is_cancelled=False):
        return StudentPractice.objects.create(
            user=user,
            practice=practice or self.practice,
            workflow_state=state,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            is_cancelled=is_cancelled,
        )

    def make_external_practice(self):
        """Externí (manuální) praxe — obsahový řetězec CONTENT_* je jen v manuální matici."""
        return Practice.objects.create(
            title="BL02 externí praxe",
            description="Syntetická externí praxe pro BL02 testy",
            employer=None,
            subject=self.subject,
            is_external=True,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=40),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            available_positions=10,
        )


class ConfirmContractAuthorizationTests(BL02FixtureMixin, TestCase):
    """BE-001 / REQ-011 — cizí aktér nemutuje cizí potvrzení smlouvy; oprávněný projde."""

    def _snapshot(self, sp):
        sp.refresh_from_db()
        return {
            "workflow_state": sp.workflow_state,
            "approval_status": sp.approval_status,
            "school_approved": sp.school_approved,
            "employer_approved": sp.employer_approved,
            "contract_received_date": sp.contract_received_date,
            "is_cancelled": sp.is_cancelled,
        }

    def _confirm(self, actor, sp):
        self.client.force_authenticate(user=actor)
        return self.client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/")

    def test_foreign_student_confirm_contract_denied_no_mutation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.APPLIED)
        before = self._snapshot(sp)

        response = self._confirm(self.foreign_student, sp)

        self.assertEqual(response.status_code, 403)
        after = self._snapshot(sp)
        self.assertEqual(after, before)
        self.assertEqual(after["workflow_state"], StudentPracticeWorkflowState.APPLIED)
        self.assertFalse(after["school_approved"])
        self.assertFalse(after["employer_approved"])
        self.assertIsNone(after["contract_received_date"])

    def test_foreign_org_confirm_contract_denied_no_mutation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.APPLIED)
        before = self._snapshot(sp)

        response = self._confirm(self.foreign_org, sp)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._snapshot(sp), before)

    def test_foreign_professor_confirm_contract_denied_no_mutation(self):
        """HEAD jiné katedry — žádný vztah k přihlášce → 403 bez mutace."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.APPLIED)
        before = self._snapshot(sp)

        response = self._confirm(self.foreign_professor, sp)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._snapshot(sp), before)

    def test_cancelled_sp_confirm_contract_denied(self):
        """IsNotCancelled: stornovanou přihlášku nepřepíše ani vlastník."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.AWAITING_CONTRACT, is_cancelled=True)
        before = self._snapshot(sp)

        response = self._confirm(self.student_owner, sp)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._snapshot(sp), before)

    def test_owner_student_confirm_is_receipt_only(self):
        """T1: owner-student = pouze potvrzení přijetí — žádná approval osa,
        žádná změna stavu ani approval_status („receipt only“).
        Fixture: AWAITING_CONTRACT (T2b povoluje jen pre-kontrakční zdrojové
        stavy; APPLIED je vyhrazen externí cestě)."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        before = self._snapshot(sp)

        response = self._confirm(self.student_owner, sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        # receipt only — přijetí smlouvy doloženo datem
        self.assertIsNotNone(sp.contract_received_date)
        # T1: approval/state DB nezměněn (žádná osa, žádný CONTRACTED)
        self.assertEqual(sp.workflow_state, before["workflow_state"])  # APPLIED
        self.assertEqual(sp.approval_status, before["approval_status"])  # PENDING
        self.assertFalse(sp.school_approved)
        self.assertFalse(sp.employer_approved)
        self.assertEqual(sp.is_cancelled, before["is_cancelled"])

    def test_school_actor_single_axis_keeps_state_pending(self):
        """T1: jedna osa (school) → zapsána jen školní osa; employer osa
        nedotčena; stav i approval_status NEZMĚNĚNY (žádný CONTRACTED)."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        before = self._snapshot(sp)

        response = self._confirm(self.garant, sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.school_approved)
        self.assertFalse(sp.employer_approved)  # cizí osa NE nastavena
        self.assertEqual(sp.workflow_state, before["workflow_state"])  # AWAITING_CONTRACT
        self.assertEqual(sp.approval_status, before["approval_status"])  # PENDING
        self.assertIsNotNone(sp.contract_received_date)

    def test_employer_actor_single_axis_keeps_state_pending(self):
        """T1: jedna osa (employer) → zapsána jen employer osa; school osa
        nedotčena; stav i approval_status NEZMĚNĚNY (žádný CONTRACTED)."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        before = self._snapshot(sp)

        response = self._confirm(self.org_user, sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.employer_approved)
        self.assertFalse(sp.school_approved)  # cizí osa NE nastavena
        self.assertEqual(sp.workflow_state, before["workflow_state"])  # AWAITING_CONTRACT
        self.assertEqual(sp.approval_status, before["approval_status"])  # PENDING
        self.assertIsNotNone(sp.contract_received_date)

    def test_superuser_single_axis_keeps_state_pending(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        before = self._snapshot(sp)

        response = self._confirm(self.admin, sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.school_approved)
        self.assertFalse(sp.employer_approved)
        self.assertEqual(sp.workflow_state, before["workflow_state"])  # AWAITING_CONTRACT
        self.assertEqual(sp.approval_status, before["approval_status"])  # PENDING

    def test_both_axes_require_separate_roles(self):
        """T1: CONTRACTED + APPROVED nastává PŘESNĚ druhou osou vlastní
        rolí; první osa stav nemění; allokační notifikace až s přechodem."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        allocation_before = Notification.objects.filter(verb="ALLOCATION_ORG", recipient=self.org_user).count()

        # 1) zaměstnavatel potvrdí svou osu — pending, žádný CONTRACTED
        response = self._confirm(self.org_user, sp)
        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.employer_approved)
        self.assertFalse(sp.school_approved)
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)  # nezměněn
        self.assertEqual(sp.approval_status, ApprovalStatus.PENDING)  # nezměněno
        # nedošlo k alokaci → žádná allokační notifikace
        self.assertEqual(
            Notification.objects.filter(verb="ALLOCATION_ORG", recipient=self.org_user).count(),
            allocation_before,
        )

        # 2) teprve škola (garant) druhou osou → CONTRACTED + APPROVED
        response = self._confirm(self.garant, sp)
        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.school_approved)
        self.assertTrue(sp.employer_approved)
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.APPROVED)
        # allokační notifikace vznikla právě s přechodem (přesně jedna navíc)
        self.assertEqual(
            Notification.objects.filter(verb="ALLOCATION_ORG", recipient=self.org_user).count(),
            allocation_before + 1,
        )

    def test_preapproved_pending_reconciled_via_transition_not_confirm(self):
        """T1/T2b + finding 6: obě osy už drží na pending řádku → opakované
        potvrzení je čistý no-op (žádný re-write data/ActionLog/notifikace);
        smír na CONTRACTED jde výslovně autorizovaným transition (T1 brána
        obě osy kontroluje na API hranici)."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        StudentPractice.objects.filter(pk=sp.pk).update(school_approved=True, employer_approved=True)
        sp.refresh_from_db()
        log_before = ActionLog.objects.count()
        alloc_before = Notification.objects.filter(verb="ALLOCATION_ORG").count()

        response = self._confirm(self.garant, sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)  # no-op, NE posun
        self.assertEqual(sp.approval_status, ApprovalStatus.PENDING)
        self.assertIsNone(sp.contract_received_date)  # žádný re-write data
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG").count(), alloc_before)

        # smír přes výslovně autorizovaný transition (obě osy drží → T1 gate OK)
        self.client.force_authenticate(user=self.garant)
        reconcile = self.client.post(
            f"/api/student-practices/{sp.student_practice_id}/transition/",
            {"target_state": StudentPracticeWorkflowState.CONTRACTED.value, "reason": "smír obou os"},
            format="json",
        )
        self.assertEqual(reconcile.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.APPROVED)
        self.assertTrue(sp.school_approved)
        self.assertTrue(sp.employer_approved)
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG").count(), alloc_before + 1)

    def test_capacity_counts_contracted_only_pending_not_counted(self):
        """T1: kapacita počítá jen CONTRACTED. Jednosá (pending) přihláška
        místo nekonzumuje; při plné kapacitě je druhá osa odmítnuta 400
        CAPACITY_FULL bez jakékoli mutace."""
        cap_practice = Practice.objects.create(
            title="BL02 kapacita 1",
            description="Syntetická praxe s kapacitou 1",
            employer=self.employer,
            subject=self.subject,
            contact_user=self.org_user,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=40),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            available_positions=1,
        )
        sp1 = self.make_sp(self.student_owner, practice=cap_practice, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        sp2 = self.make_sp(self.foreign_student, practice=cap_practice, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)

        # SP1: první osa → pending, místo NEkonzumuje (0/1 obsazeno)
        response = self._confirm(self.org_user, sp1)
        self.assertEqual(response.status_code, 200)
        sp1.refresh_from_db()
        self.assertEqual(sp1.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        self.assertTrue(sp1.employer_approved)
        self.assertFalse(sp1.school_approved)

        # SP2: první osa → pending (stále nekonzumuje)
        response = self._confirm(self.org_user, sp2)
        self.assertEqual(response.status_code, 200)
        sp2.refresh_from_db()
        self.assertEqual(sp2.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)

        # SP2: druhá osa → CONTRACTED = první konzumované místo
        response = self._confirm(self.garant, sp2)
        self.assertEqual(response.status_code, 200)
        sp2.refresh_from_db()
        self.assertEqual(sp2.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp2.approval_status, ApprovalStatus.APPROVED)

        # CONTRACTED-only: jediný CONTRACTED = SP2; pending SP1 se nepočítá
        contracted_count = StudentPractice.objects.filter(
            practice=cap_practice,
            workflow_state=StudentPracticeWorkflowState.CONTRACTED,
        ).count()
        self.assertEqual(contracted_count, 1)

        # Kapacita plná: SP1 druhá osa → 400, žádná mutace (před zápisem)
        before = self._snapshot(sp1)
        response = self._confirm(self.garant, sp1)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error_code"), "CAPACITY_FULL")
        self.assertEqual(self._snapshot(sp1), before)


class EvaluationAuthorizationTests(BL02FixtureMixin, TestCase):
    """BE-002 — žádné cizí čtení/mutace evaluací; vlastník a příslušný garant čtou."""

    SENTINEL = "BL02_SYNTHETIC_EVALUATION_SENTINEL"

    def _make_evaluation(self, sp):
        return Evaluation.objects.create(
            student_practice=sp,
            expertise_comment=self.SENTINEL,
            evaluated_by=self.garant,
        )

    def _detail_url(self, evaluation):
        return f"/api/student-practices/evaluations/{evaluation.evaluation_id}/"

    def _payload(self, sp):
        return {
            "student_practice_id": sp.student_practice_id,
            "expertise_rating": 5,
            "expertise_comment": "BL02 synthetic payload",
            "communication_rating": 4,
            "communication_comment": "BL02 synthetic payload",
            "initiative_rating": 5,
            "initiative_comment": "BL02 synthetic payload",
            "overall_comment": "BL02 synthetic payload",
            "pdf_file": SimpleUploadedFile("bl02.pdf", b"%PDF-1.4 bl02 synthetic", content_type="application/pdf"),
        }

    def test_foreign_student_cannot_read_evaluation_detail(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.foreign_student)
        response = self.client.get(self._detail_url(evaluation))

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(self.SENTINEL.encode(), response.content)
        self.assertTrue(Evaluation.objects.filter(pk=evaluation.pk).exists())

    def test_foreign_student_evaluation_list_is_empty(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        self._make_evaluation(sp)

        self.client.force_authenticate(user=self.foreign_student)
        response = self.client.get("/api/student-practices/evaluations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.data), [])
        self.assertNotIn(self.SENTINEL.encode(), response.content)

    def test_foreign_student_cannot_update_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.foreign_student)
        response = self.client.patch(self._detail_url(evaluation), {"expertise_comment": "hacked"}, format="json")

        # studentská role nemá write právo vůbec (MAJOR-1) → 403, žádná mutace
        self.assertEqual(response.status_code, 403)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.expertise_comment, self.SENTINEL)

    def test_foreign_student_cannot_delete_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.foreign_student)
        response = self.client.delete(self._detail_url(evaluation))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Evaluation.objects.filter(pk=evaluation.pk).exists())

    def test_foreign_professor_cannot_update_evaluation(self):
        """Pedagog jiné katedry (v roli, která má write) — mimo scope → 404."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.foreign_professor)
        response = self.client.patch(
            self._detail_url(evaluation),
            {"expertise_comment": "hacked", "pdf_file": SimpleUploadedFile("x.pdf", b"%PDF-1.4 x", content_type="application/pdf")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.expertise_comment, self.SENTINEL)

    def test_foreign_org_cannot_update_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.foreign_org)
        response = self.client.patch(self._detail_url(evaluation), {"expertise_comment": "hacked"}, format="json")

        self.assertEqual(response.status_code, 404)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.expertise_comment, self.SENTINEL)

    def test_foreign_student_cannot_create_evaluation_on_foreign_sp(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)

        self.client.force_authenticate(user=self.foreign_student)
        response = self.client.post("/api/student-practices/evaluations/", self._payload(sp))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Evaluation.objects.filter(student_practice=sp).exists())

    def test_owner_student_reads_own_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.student_owner)
        response = self.client.get(self._detail_url(evaluation))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["expertise_comment"], self.SENTINEL)

    def test_department_garant_reads_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.garant)
        response = self.client.get(self._detail_url(evaluation))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["expertise_comment"], self.SENTINEL)

    # ------------------------------------------------------------------
    # MAJOR-1: read vs write split — student NESMÍ psát mentorskou evaluaci
    # ------------------------------------------------------------------

    def test_owner_student_cannot_create_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)

        self.client.force_authenticate(user=self.student_owner)
        response = self.client.post("/api/student-practices/evaluations/", self._payload(sp))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Evaluation.objects.filter(student_practice=sp).exists())

    def test_owner_student_cannot_update_own_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.student_owner)
        response = self.client.patch(
            self._detail_url(evaluation),
            {"expertise_comment": "student tampered"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.expertise_comment, self.SENTINEL)

    def test_owner_student_cannot_delete_own_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.student_owner)
        response = self.client.delete(self._detail_url(evaluation))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Evaluation.objects.filter(pk=evaluation.pk).exists())

    # ------------------------------------------------------------------
    # MINOR: oprávněný mentor (katedra) — create / update / delete + DB důkaz
    # ------------------------------------------------------------------

    def test_professor_creates_evaluation_on_ended_sp(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)

        self.client.force_authenticate(user=self.garant)
        response = self.client.post("/api/student-practices/evaluations/", self._payload(sp))

        self.assertEqual(response.status_code, 201)
        evaluation = Evaluation.objects.get(student_practice=sp)
        self.assertEqual(evaluation.evaluated_by_id, self.garant.pk)

    def test_professor_updates_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.garant)
        response = self.client.patch(
            self._detail_url(evaluation),
            {
                "expertise_comment": "Mentor updated",
                "pdf_file": SimpleUploadedFile("bl02.pdf", b"%PDF-1.4 bl02 synthetic", content_type="application/pdf"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.expertise_comment, "Mentor updated")

    def test_professor_deletes_evaluation(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)

        self.client.force_authenticate(user=self.garant)
        response = self.client.delete(self._detail_url(evaluation))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Evaluation.objects.filter(pk=evaluation.pk).exists())

    # ------------------------------------------------------------------
    # BLOCKER-2: student_practice_id je neměnný — pokus o reassignace → 400
    # ------------------------------------------------------------------

    def test_evaluation_student_practice_id_immutable_on_update(self):
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.ENDED)
        evaluation = self._make_evaluation(sp)
        foreign_sp = self.make_sp(self.foreign_student, state=StudentPracticeWorkflowState.ENDED)

        self.client.force_authenticate(user=self.garant)
        response = self.client.patch(
            self._detail_url(evaluation),
            {"student_practice_id": foreign_sp.student_practice_id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        # custom exception handler: {"error_code": ..., "details": {field: [...]}}
        details = response.data.get("details", response.data)
        self.assertIn("student_practice_id", details)
        evaluation.refresh_from_db()
        # Persisted before/after: relace zůstává na PŮVODNÍ přihlášce
        self.assertEqual(evaluation.student_practice_id, sp.student_practice_id)
        self.assertFalse(Evaluation.objects.filter(student_practice=foreign_sp).exists())


class RepairTransitionAuthorizationTests(BL02FixtureMixin, TestCase):
    """BE-015 — cizí studentský opravný transition odmítnut bez mutace; vlastník opraví."""

    def _snapshot(self, sp):
        sp.refresh_from_db()
        return {
            "workflow_state": sp.workflow_state,
            "is_cancelled": sp.is_cancelled,
            "approval_status": sp.approval_status,
            "progress_status": sp.progress_status,
        }

    def _transition(self, actor, sp, target_state):
        self.client.force_authenticate(user=actor)
        return self.client.post(
            f"/api/student-practices/{sp.student_practice_id}/transition/",
            {"target_state": target_state.value, "reason": "BL02 synthetic repair"},
            format="json",
        )

    def test_foreign_student_cannot_repair_documents_rejected(self):
        """Cizí student je odmítnut na každé hrane opravného cyklu (BE-015).
        BL-03/T2c: přímá hrana DOCUMENTS_REJECTED → ENDED pro studenty
        neexistuje (matrix ji odstranila) → odmítnutí přichází jako 400
        „Student nemůže provést tento přechod“ dřív než ownership guard."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        before = self._snapshot(sp)

        response = self._transition(self.foreign_student, sp, StudentPracticeWorkflowState.ENDED)

        self.assertIn(response.status_code, (400, 403))
        after = self._snapshot(sp)
        self.assertEqual(after, before)
        self.assertEqual(after["workflow_state"], StudentPracticeWorkflowState.DOCUMENTS_REJECTED)

    def test_foreign_student_cannot_repair_content_rejected(self):
        external = self.make_external_practice()
        sp = self.make_sp(self.student_owner, practice=external, state=StudentPracticeWorkflowState.CONTENT_REJECTED)
        before = self._snapshot(sp)

        response = self._transition(self.foreign_student, sp, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL)

        self.assertEqual(response.status_code, 403)
        after = self._snapshot(sp)
        self.assertEqual(after, before)
        self.assertEqual(after["workflow_state"], StudentPracticeWorkflowState.CONTENT_REJECTED)

    def test_owner_student_repairs_documents_rejected(self):
        """C19-B/T2c (BL-03 supersede): vlastník opravuje přes UPLOAD —
        stav DOCUMENTS_RESUBMITTED (review-pending), NE přímý přechod
        do ENDED (hrana odstraněna; upload ≠ approval)."""
        sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        doc = UploadedDocument.objects.create(document_type=DocumentType.CONTRACT, status=DocumentStatus.REJECTED)
        sp.contract_document = doc
        sp.save(update_fields=["contract_document"])

        self.client.force_authenticate(user=self.student_owner)
        response = self.client.post(
            f"/api/student-practices/upload-document/{doc.pk}",
            {"document": SimpleUploadedFile("repaired.pdf", b"%PDF-1.4 bl02 repair", content_type="application/pdf")},
        )

        self.assertEqual(response.status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.PENDING)  # čeká na review

    def test_owner_student_repairs_content_rejected(self):
        external = self.make_external_practice()
        sp = self.make_sp(self.student_owner, practice=external, state=StudentPracticeWorkflowState.CONTENT_REJECTED)

        response = self._transition(self.student_owner, sp, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL)
