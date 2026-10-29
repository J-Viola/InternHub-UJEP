"""BL-08 GO-5 — deterministický demo seed (BL08-SEED-v1).

Ne-dstruktivní, idempotentní (get_or_create) seed podle
``app/fixtures/demo_seed_spec.json`` + SYNTHETIC_DATA_PLAN.md:
fixní syntetické identity na vyhrazené doméně ``.test.local``, fixní
stavové fixture F1–F9 (+ F4b opravný stav DOCUMENTS_RESUBMITTED), žádná
náhoda, žádné PII, žádná hesla v repu.

- ``--password`` / env ``DEMO_SEED_PASSWORD`` — jinak se heslo vygeneruje
  jednou a vytiskne; do DB se ukládá jen hash, a jen při vytvoření účtu.
- ``--reset`` — smaže JEN demo řádky (reserved e-maily/tituly) a jen pokud
  BL-07 DB-identity guard schválí disposable cílovou DB (stejně jako flush).
- ``seed_fake`` se nepoužívá ani nemění (náhodný + destruktivní).
"""

import json
import os
import secrets
from datetime import UTC, date, datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from app.db_identity import NonDisposableDatabaseError, assert_disposable_db
from department.models import Department
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import (
    DocumentStatus,
    DocumentType,
    Evaluation,
    PracticeRegistration,
    StudentPractice,
    StudentPracticeWorkflowState,
    UploadedDocument,
)
from student_practices.services import ensure_practice_registration
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

SEED_ID = "BL08-SEED-v1"
SEED_USERNAME_PREFIX = "bl08-seed-v1:"
PASSWORD_ENV = "DEMO_SEED_PASSWORD"
DEMO_SPEC_DEFAULT = Path(__file__).resolve().parents[2] / "fixtures" / "demo_seed_spec.json"  # A-04: verzovaná fixture v repu

# Fixní (deterministické) časové konstanty — žádné now() v datech seedu.
OFFER_START = date(2027, 3, 1)
OFFER_END = date(2027, 6, 30)
CONTRACT_FIXED = datetime(2027, 3, 2, 9, 0, tzinfo=UTC)
CANCEL_REQUEST_FIXED = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
MARKER_DATE = datetime(2027, 1, 1, 0, 0, tzinfo=UTC)

ORG_COMPANY = "SYNTHETIC DEMO DATA — Demo Firma Demo s.r.o."
ORG_ICO = "00000000"  # syntetické; checksum neodpovídá reálnému IČO
DEMO_SUBJECT_CODE = "DEMO-PRAXE"
DEMO_DEPARTMENT_CODES = ["DEMO-KI", "DEMO-MA"]
DEMO_CANCELLATION_REASON = "SYNTHETIC DEMO: storno studentem (minulý rok, vzato na vědomí — A-12)."

# Nabídky: (titulek, kapacita, employment_type) — F1..F9 + F4b + F7 triáda.
OFFER_SPECS = [
    ("DEMO Kapacita 1", 1, ""),  # F1
    ("DEMO Standard", 5, ""),  # F2
    ("DEMO Předsmluvní", 5, ""),  # F3 (additive: vlastní nabídka)
    ("DEMO Smlouvy", 5, ""),  # F4
    ("DEMO Oprava", 5, ""),  # F4b (additive: DOCUMENTS_RESUBMITTED)
    ("DEMO Smlouvy 2", 5, ""),  # F5
    ("DEMO Dokončení", 5, ""),  # F6
    ("DEMO Úvazek A", 5, "uvazek_0_5"),  # F7
    ("DEMO Úvazek B", 5, "uvazek_1_0"),  # F7
    ("DEMO Úvazek C", 5, ""),  # F7
    ("DEMO Storno", 5, ""),  # F9 (additive: storno studentem)
]
OFFER_TITLES = [t for t, _cap, _emp in OFFER_SPECS]


class Command(BaseCommand):
    help = "Deterministický demo seed BL08-SEED-v1 (ne-dstruktivní, idempotentní). " "Viz app/fixtures/demo_seed_spec.json."

    def add_arguments(self, parser):
        parser.add_argument("--spec", default=str(DEMO_SPEC_DEFAULT), help="Cesta k demo_seed_spec.json.")
        parser.add_argument("--password", default=None, help="Demo heslo účtů (neukládá se; jen hash).")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Nejprve smaže demo řádky (JEN na BL-07 disposable DB — jinak odmítnuto).",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        spec_path = Path(options["spec"])
        if not spec_path.exists():
            raise CommandError(f"Spec nenalezen: {spec_path}")
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if spec.get("seed_id") != SEED_ID:
            raise CommandError(f"Neočekávané seed_id v specu: {spec.get('seed_id')!r} (očekáváno {SEED_ID!r})")

        password = options.get("password") or os.environ.get(PASSWORD_ENV)
        generated = False
        if not password:
            password = secrets.token_urlsafe(12)
            generated = True

        if options.get("reset"):
            # BL-07 guard: --reset jen na disposable test DB (fail-closed).
            try:
                assert_disposable_db("seed_demo --reset", force=True)
            except NonDisposableDatabaseError as e:
                raise CommandError(f"seed_demo --reset odmítnut BL-07 DB-identity guardem: {e}")
            self._reset()
            self.stdout.write(self.style.WARNING("seed_demo: demo řádky smazány (--reset)."))

        with transaction.atomic():
            self._preflight(spec)
            ctx = self._seed(spec, password)

        self._verify_and_report(spec, ctx)

        if generated:
            self.stdout.write(self.style.WARNING(f"DEMO HESLO (vygenerováno jednorázově, NEukládá se): {password}"))
        else:
            self.stdout.write("Demo heslo nastaveno přes --password/env (nevytištěno, jen hash v DB).")

    # ------------------------------------------------------------------
    @staticmethod
    def _preflight(spec):
        """A-18: před jakýmkoli zápisem odmítne kolizi s cizími (ne-seedovými) daty.

        ``get_or_create`` podle e-mailu / kódu předmětu / titulku by jinak převzalo cizí
        řádek a seed by ho přepsal (správce předmětu) nebo mu připojil demo vazby.
        """
        problems = []

        emails = [a["email"] for a in spec.get("accounts", [])]
        for user in get_user_model().objects.filter(email__in=emails):
            if not (user.username or "").startswith(SEED_USERNAME_PREFIX):
                problems.append(f"účet {user.email} už existuje a není seedový")

        subject = Subject.objects.filter(subject_code=DEMO_SUBJECT_CODE).select_related("subject_manager").first()
        if subject is not None:
            manager = subject.subject_manager
            seed_owned = (manager is not None and (manager.username or "").startswith(SEED_USERNAME_PREFIX)) or (
                manager is None
                and not subject.practices.exists()
                and not subject.practice_registrations.exists()
                and not subject.user_subjects.exists()
            )
            if not seed_owned:
                problems.append(f"předmět {DEMO_SUBJECT_CODE} už existuje a patří jinému správci / má data")

        org_user = OrganizationUser.objects.filter(username__startswith=SEED_USERNAME_PREFIX, employer_profile__isnull=False).first()
        seed_employer_id = org_user.employer_profile_id if org_user else None
        foreign_titles = (
            Practice.objects.filter(title__in=OFFER_TITLES).exclude(employer_id=seed_employer_id).values_list("title", flat=True)
            if seed_employer_id
            else Practice.objects.filter(title__in=OFFER_TITLES).values_list("title", flat=True)
        )
        for title in sorted(set(foreign_titles)):
            problems.append(f"nabídka „{title}“ už existuje u jiného zaměstnavatele")

        if problems:
            raise CommandError(
                "seed_demo: kolize s existujícími daty, nic nebylo zapsáno — " + "; ".join(problems) + ". "
                "Přejmenujte / odstraňte cizí řádky, nebo použijte --reset na disposable DB."
            )

    @staticmethod
    def _password_user(user, password):
        user.set_password(password)
        user.save()
        return user

    def _get_user(self, account, password, departments):
        role = account["role"]
        email = account["email"]
        first, last = "Demo", account["key"].replace("demo-", "").title()
        if role == "admin":
            user, created = get_user_model().objects.get_or_create(
                email=email,
                defaults={
                    "username": SEED_USERNAME_PREFIX + account["key"],
                    "first_name": first,
                    "last_name": last,
                    "is_active": True,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
        elif role in ("VY", "VK"):
            defaults = {
                "first_name": first,
                "username": SEED_USERNAME_PREFIX + account["key"],
                "last_name": last,
                "is_active": True,
                "department": departments[account["department"]],
                "department_role": DepartmentRole.HEAD if role == "VK" else DepartmentRole.TEACHER,
            }
            if role == "VY":
                defaults["is_garant_praxe"] = True
            user, created = ProfessorUser.objects.get_or_create(email=email, defaults=defaults)
        elif role == "OWNER":
            user, created = OrganizationUser.objects.get_or_create(
                email=email,
                defaults={
                    "username": SEED_USERNAME_PREFIX + account["key"],
                    "first_name": first,
                    "last_name": last,
                    "is_active": True,
                    "organization_role": OrganizationRole.OWNER,
                },
            )
            # A-18: profil se hledá přes FK na straně OrganizationUser; PK se nevynucuje
            # (dřívější ``employer_id=user.pk`` mohlo převzít cizí profil se shodným PK).
            profile = user.employer_profile
            if profile is None:
                profile = EmployerProfile.objects.create(company_name=ORG_COMPANY, ico=ORG_ICO, approval_status=ApprovalStatus.APPROVED)
                user.employer_profile = profile
                user.save()
        else:  # ST
            user, created = StudentUser.objects.get_or_create(
                email=email,
                defaults={
                    "username": SEED_USERNAME_PREFIX + account["key"],
                    "first_name": first,
                    "last_name": last,
                    "is_active": True,
                },
            )
        if created:
            Command._password_user(user, password)
        return user

    def _get_practice(self, title, capacity, employment_type, subject, employer):
        practice, _created = Practice.objects.get_or_create(
            title=title,
            defaults={
                "description": "SYNTHETIC DEMO DATA — deterministický demo seed (BL08-SEED-v1).",
                "employer": employer,
                "subject": subject,
                "start_date": OFFER_START,
                "end_date": OFFER_END,
                "is_active": True,
                "approval_status": ApprovalStatus.APPROVED,
                "progress_status": ProgressStatus.NOT_STARTED,
                "workflow_state": PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
                "available_positions": capacity,
                "employment_type": employment_type,
            },
        )
        return practice

    def _get_sp(
        self,
        *,
        user,
        practice,
        state,
        year,
        school_approved=False,
        employer_approved=False,
        approval_status=ApprovalStatus.PENDING,
        contract_received_date=None,
        cancellation_requested_at=None,
        cancellation_resolved_at=None,
        cancellation_reason=None,
        cancelled_from_state=None,
        contract_doc=False,
        contract_status=DocumentStatus.PENDING,
    ):
        registration = ensure_practice_registration(user, practice.subject_id, year)
        sp, created = StudentPractice.objects.get_or_create(
            user=user,
            practice=practice,
            is_cancelled=cancellation_requested_at is not None,
            defaults={
                "application_date": OFFER_START,
                "workflow_state": None if cancellation_requested_at else state,
                "approval_status": ApprovalStatus.REJECTED if cancellation_requested_at else approval_status,
                "hours_completed": 0,
                "year": year,
                "start_date": OFFER_START,
                "end_date": OFFER_END,
                "school_approved": school_approved,
                "employer_approved": employer_approved,
                "contract_received_date": contract_received_date,
                "cancellation_requested_at": cancellation_requested_at,
                "cancellation_resolved_at": cancellation_resolved_at,
                "cancelled_from_state": cancelled_from_state,
                "cancelled_at": cancellation_requested_at,
                "progress_status": ProgressStatus.CANCELLED if cancellation_requested_at else ProgressStatus.NOT_STARTED,
                # cancellation_reason je NOT NULL bez defaultu → "" místo None
                "cancellation_reason": cancellation_reason or "",
                "registration": registration,
            },
        )
        if not created and sp.registration_id is None:
            sp.registration = registration
            sp.save(update_fields=["registration"])
        if contract_doc and sp.contract_document_id is None:
            doc = UploadedDocument.objects.create(document_type=DocumentType.CONTRACT, status=contract_status)
            sp.contract_document = doc
            sp.save(update_fields=["contract_document"])
        elif contract_doc and contract_status == DocumentStatus.APPROVED and sp.contract_document.status != DocumentStatus.APPROVED:
            # A-11: CONTRACTED fixture musí mít schválenou smlouvu i při opakovaném seedu
            sp.contract_document.status = DocumentStatus.APPROVED
            sp.contract_document.save(update_fields=["status"])
        return sp

    def _seed(self, spec, password):
        ctx = {"users": {}, "practices": {}, "sps": {}}

        # 1) katedry + 2) předmět (ze specu)
        departments = {}
        for dep in spec["departments"]:
            obj, _ = Department.objects.get_or_create(department_code=dep["code"], defaults={"department_name": dep["name"]})
            departments[dep["code"]] = obj

        subject_spec = spec["subjects"][0]
        subject, _ = Subject.objects.get_or_create(
            subject_code=subject_spec["code"],
            defaults={"subject_name": subject_spec["name"], "department": departments[subject_spec["department"]]},
        )

        # 3) účty
        for account in spec["accounts"]:
            ctx["users"][account["key"]] = self._get_user(account, password, departments)

        # subject_manager dle spec (flag demo-garant)
        Subject.objects.filter(pk=subject.pk).update(subject_manager=ctx["users"]["demo-garant"])

        employer = ctx["users"]["demo-org"].employer_profile
        year = date.today().year

        # 4) nabídky (F1–F7, F9)
        for title, capacity, employment_type in OFFER_SPECS:
            ctx["practices"][title] = self._get_practice(title, capacity, employment_type, subject, employer)

        # 5) stavové fixture SP řádky (F1–F6 + F4b, F9; F8 = nic předseedováno)
        st = StudentPracticeWorkflowState
        ctx["sps"]["F1"] = self._get_sp(
            user=ctx["users"]["demo-student2"],
            practice=ctx["practices"]["DEMO Kapacita 1"],
            state=st.CONTRACTED,
            year=year,
            school_approved=True,
            employer_approved=True,
            approval_status=ApprovalStatus.APPROVED,
            contract_doc=True,
            contract_status=DocumentStatus.APPROVED,
            contract_received_date=CONTRACT_FIXED,
        )
        ctx["sps"]["F2"] = self._get_sp(
            user=ctx["users"]["demo-student"],
            practice=ctx["practices"]["DEMO Standard"],
            state=st.APPLIED,
            year=year,
        )
        ctx["sps"]["F3"] = self._get_sp(
            user=ctx["users"]["demo-student"],
            practice=ctx["practices"]["DEMO Předsmluvní"],
            state=st.AWAITING_CONTRACT,
            year=year,
        )
        ctx["sps"]["F4"] = self._get_sp(
            user=ctx["users"]["demo-student"],
            practice=ctx["practices"]["DEMO Smlouvy"],
            state=st.AWAITING_DOCUMENTS,
            year=year,
            contract_doc=True,
        )
        # F4b (additive, GO-05): restartovací fixture opravné smyčky (T2c/C19-B)
        # — DOCUMENTS_RESUBMITTED = „upload ≠ approval", doklad PENDING;
        # F4 zůstává výchozím stavem kroku 1 (zamítnutí → DOCUMENTS_REJECTED).
        ctx["sps"]["F4b"] = self._get_sp(
            user=ctx["users"]["demo-student"],
            practice=ctx["practices"]["DEMO Oprava"],
            state=st.DOCUMENTS_RESUBMITTED,
            year=year,
            contract_doc=True,
        )
        ctx["sps"]["F5"] = self._get_sp(
            user=ctx["users"]["demo-student2"],
            practice=ctx["practices"]["DEMO Smlouvy 2"],
            state=st.CONTRACTED,
            year=year,
            school_approved=True,
            employer_approved=True,
            approval_status=ApprovalStatus.APPROVED,
            contract_doc=True,
            contract_status=DocumentStatus.APPROVED,
            contract_received_date=CONTRACT_FIXED,
        )
        ctx["sps"]["F6"] = self._get_sp(
            user=ctx["users"]["demo-student"],
            practice=ctx["practices"]["DEMO Dokončení"],
            state=st.ENDED,
            year=year,
        )
        # F9 (additive): storno studentem (A-12, okamžité) na LOŇSKÉ registraci, už vzaté
        # garantem na vědomí — nevyřízené storno by blokovalo další žádosti demo studenta.
        ctx["sps"]["F9"] = self._get_sp(
            user=ctx["users"]["demo-student"],
            practice=ctx["practices"]["DEMO Storno"],
            state=st.CONTRACTED,
            year=year - 1,
            school_approved=True,
            employer_approved=True,
            approval_status=ApprovalStatus.APPROVED,
            contract_doc=True,
            contract_status=DocumentStatus.APPROVED,
            contract_received_date=CONTRACT_FIXED,
            cancellation_requested_at=CANCEL_REQUEST_FIXED,
            cancellation_resolved_at=CANCEL_REQUEST_FIXED,
            cancelled_from_state=st.CONTRACTED,
            cancellation_reason=DEMO_CANCELLATION_REASON,
        )

        # 6) marker seed_id do DB (verifikace „zapiš do DB" — SYNTHETIC_DATA_PLAN §3)
        ActionLog.objects.get_or_create(
            object_type="DemoSeed",
            action_description=SEED_ID,
            defaults={"action_type": "DEMO_SEED", "action_date": MARKER_DATE, "user": ctx["users"]["demo-admin"]},
        )
        return ctx

    # ------------------------------------------------------------------
    @staticmethod
    def _reset():
        """Smaže jen řádky s prokazatelným markerem vlastnictví seedu; volá se
        až po schválení BL-07 guardem."""
        demo_users = get_user_model().objects.filter(username__startswith=SEED_USERNAME_PREFIX)
        demo_user_ids = list(demo_users.values_list("pk", flat=True))
        demo_profile_ids = list(
            OrganizationUser.objects.filter(username__startswith=SEED_USERNAME_PREFIX).values_list("employer_profile_id", flat=True)
        )
        owned_practices = Practice.objects.filter(
            title__in=OFFER_TITLES,
            employer__organization_users__username__startswith=SEED_USERNAME_PREFIX,
        ).distinct()
        owned_practice_ids = list(owned_practices.values_list("pk", flat=True))
        sp_qs = StudentPractice.objects.filter(Q(practice_id__in=owned_practice_ids) | Q(user_id__in=demo_user_ids))
        doc_ids = [i for i in sp_qs.values_list("contract_document_id", flat=True) if i]
        sp_qs.delete()  # SP nemá FK z UploadedDocument → mazání SP je bezpečné
        UploadedDocument.objects.filter(pk__in=doc_ids).delete()
        PracticeRegistration.objects.filter(student_id__in=demo_user_ids).delete()
        owned_practices.delete()
        # EmployerProfile.employer_id je AUTO PK (FK je na straně org) —
        # demo profil má PK == demo org pk (viz _get_user).
        EmployerProfile.objects.filter(pk__in=demo_profile_ids).delete()
        demo_subjects = Subject.objects.filter(
            subject_code=DEMO_SUBJECT_CODE,
            subject_manager__username__startswith=SEED_USERNAME_PREFIX,
            practices__isnull=True,
            practice_registrations__isnull=True,
            user_subjects__isnull=True,
        ).distinct()
        demo_subject_ids = list(demo_subjects.values_list("pk", flat=True))
        demo_users.delete()
        Subject.objects.filter(pk__in=demo_subject_ids).delete()
        # Department nemá seed-owner pole a může být sdílená uživateli/předměty;
        # její vlastnictví nelze bezpečně doložit, proto ji reset záměrně ponechá.
        ActionLog.objects.filter(object_type="DemoSeed", action_description=SEED_ID).delete()

    # ------------------------------------------------------------------
    def _verify_and_report(self, spec, ctx):
        """Verifikační tabulka dle SYNTHETIC_DATA_PLAN.md §3 — deterministic
        controlní součty + dosažitelnost F1–F9 vč. F4b; jakýkoli FAIL = 400."""
        st = StudentPracticeWorkflowState
        lines = ["=== BL08-SEED-v1 demo seed — verifikace ==="]
        failures = []

        def check(label, ok):
            lines.append(f"  {label}: {'OK' if ok else 'FAIL'}")
            if not ok:
                failures.append(label)

        emails = [a["email"] for a in spec["accounts"]]
        users = get_user_model().objects.filter(email__in=emails)
        check("role účtů == 7", users.count() == 7)
        check("všechny e-maily na @test.local", all(u.email.endswith("@test.local") for u in users))
        practice_count = Practice.objects.filter(title__in=OFFER_TITLES).count()
        check(f"Practice == {len(OFFER_TITLES)} (F1,F2,F3,F4,F4b,F5,F6,F7×3,F9)", practice_count == len(OFFER_TITLES))

        sps = ctx["sps"]
        check("F1: demo-student2 CONTRACTED (kapacita 1 obsazena)", sps["F1"].workflow_state == st.CONTRACTED)
        f1_pr = sps["F1"].practice
        check("F1: available_positions == 1", f1_pr.available_positions == 1)
        check("F2: demo-student APPLIED", sps["F2"].workflow_state == st.APPLIED)
        check(
            "F3: demo-student AWAITING_CONTRACT, obě osy=False",
            sps["F3"].workflow_state == st.AWAITING_CONTRACT and not sps["F3"].school_approved and not sps["F3"].employer_approved,
        )
        f4_doc = sps["F4"].contract_document
        check(
            "F4: AWAITING_DOCUMENTS + CONTRACT doklad PENDING",
            sps["F4"].workflow_state == st.AWAITING_DOCUMENTS and f4_doc is not None and f4_doc.status == DocumentStatus.PENDING,
        )
        check("F5: demo-student2 CONTRACTED", sps["F5"].workflow_state == st.CONTRACTED)
        check(
            "A-11: každé CONTRACTED fixture má schválený smluvní dokument (F1, F5, F9)",
            all(
                (sps[k].workflow_state == st.CONTRACTED or sps[k].cancelled_from_state == st.CONTRACTED)
                and sps[k].contract_document is not None
                and sps[k].contract_document.status == DocumentStatus.APPROVED
                for k in ("F1", "F5", "F9")
            ),
        )
        f4b = sps["F4b"]
        check(
            "F4b: DOCUMENTS_RESUBMITTED (review-pending oprava) + CONTRACT doklad PENDING",
            f4b.workflow_state == st.DOCUMENTS_RESUBMITTED
            and f4b.contract_document is not None
            and f4b.contract_document.status == DocumentStatus.PENDING
            and not f4b.school_approved
            and not f4b.employer_approved,
        )
        check(
            "F6: ENDED bez Evaluation",
            sps["F6"].workflow_state == st.ENDED and not Evaluation.objects.filter(student_practice=sps["F6"]).exists(),
        )
        f7_types = [
            ctx["practices"]["DEMO Úvazek A"].employment_type,
            ctx["practices"]["DEMO Úvazek B"].employment_type,
            ctx["practices"]["DEMO Úvazek C"].employment_type,
        ]
        check("F7: employment_type uvazek_0_5/uvazek_1_0/empty", f7_types == ["uvazek_0_5", "uvazek_1_0", ""])
        f9 = sps["F9"]
        check(
            "F9: storno studentem (A-12), vzaté na vědomí",
            f9.cancellation_requested_at is not None
            and f9.cancellation_resolved_at is not None
            and f9.is_cancelled
            and f9.year == date.today().year - 1,
        )

        registrations = PracticeRegistration.objects.filter(student__email__in=emails)
        check("registrace (BL-10) == 3 klíče", registrations.count() == 3)
        marker = ActionLog.objects.filter(object_type="DemoSeed", action_description=SEED_ID).first()
        check("seed_id zapsán v DB (ActionLog DemoSeed)", marker is not None and marker.action_description == SEED_ID)

        self.stdout.write("\n".join(lines))
        self.stdout.write(
            "  — součty: "
            f"users={users.count()}, practices={Practice.objects.filter(title__in=OFFER_TITLES).count()}, "
            f"student_practices={StudentPractice.objects.filter(Q(practice__title__in=OFFER_TITLES)).count()}, "
            f"registrations={registrations.count()}, seed_id={SEED_ID}"
        )
        if failures:
            raise CommandError("Seed verification SELHALA: " + "; ".join(failures))
        self.stdout.write(self.style.SUCCESS(f"Seed OK — {SEED_ID}"))
