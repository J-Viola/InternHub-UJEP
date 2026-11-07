import csv
import io

import openpyxl
from openpyxl.styles import Font, PatternFill

from student_practices.models import StudentPractice


def _escape_formula_cell(value):
    """Prefix spreadsheet formula-leading text with an apostrophe."""
    if isinstance(value, str) and (value.startswith(("=", "+", "-", "@", "\t", "\r")) or value.lstrip().startswith(("=", "+", "-", "@"))):
        return f"'{value}"
    return value


def _garant_names_for_practice(practice, memo=None):
    """
    Vrátí jména garantů dané praxe spojená čárkou.

    Prázdný řetězec, pokud žádného garanta nelze určit.
    ``memo`` (dict) cacheuje výsledek dle (subject_manager_id, department_id) —
    rezoluce na nich závisí, takže export řádků s N praxemi provede jen
    omezený počet dotazů (review B1: N+1 fix).
    """
    if practice is None:
        return ""
    try:
        from notifications.services import NotificationService

        key = None
        subject = practice.subject if practice.subject_id else None
        if subject is not None:
            key = (subject.subject_manager_id, subject.department_id)
            if memo is not None and key in memo:
                return memo[key]

        recipients = NotificationService.resolve_garant_recipients(practice)
        result = ", ".join(r.full_name for r in recipients if getattr(r, "full_name", ""))
        if memo is not None and key is not None:
            memo[key] = result
        return result
    except Exception:
        return ""


class ExportService:
    @staticmethod
    def get_scope_filters(user):
        """
        Vrátí trojici (dept_ids, employer, owner_user) pro role-based
        scoping exportu.

        Fail-closed kontrakt (BE-003 / MAJOR-2):
        - superuser → (None, None, None) — jediný neomezený rozsah
        - user=None / neznámá role → ([], None, None) — prázdný rozsah
        - StudentUser → ([], None, user) — PŘESNÁ množina vlastních
          přihlášek; nikdy katedrní data vrstevníků (žádný department-wide)
        - jinak je dept_ids VŽDY seznam (může být prázdný); prázdný seznam
          bez employer a bez owner_user znamená prázdný rozsah — volající
          musí vrátit 403, NIKDY neomezený queryset

        - garant / profesor katedry → jen praxe svého departmentu
          (practice.subject.department); primárně user.department,
          doplňkově departmenty z user_subjects
        - organizace → jen praxe vlastní employer_profile
        """
        if user is None:
            return [], None, None
        if user.is_superuser:
            return None, None, None

        from users.models import ProfessorUser, StudentUser

        dept_ids: list[int] = []
        employer = None
        owner_user = None

        if isinstance(user, ProfessorUser):
            if user.department_id:
                dept_ids.append(user.department_id)
            # Fallback: departmenty, na kterých uživatel učí
            if hasattr(user, "user_subjects"):
                dept_ids.extend(user.user_subjects.values_list("subject__department_id", flat=True).distinct())
            dept_ids = list(dict.fromkeys(d for d in dept_ids if d))
        elif isinstance(user, StudentUser):
            # Přesná autorizovaná množina = jen vlastní přihlášky studenta.
            # Katedra z jeho předmětů by zahrnula cizí vrstevníky (MAJOR-2).
            owner_user = user

        if hasattr(user, "employer_profile") and user.employer_profile:
            employer = user.employer_profile

        return dept_ids, employer, owner_user

    @staticmethod
    def apply_scope(qs, dept_ids: list[int] | None = None, employer=None, owner_user=None):
        """
        Aplikuje role scope na queryset exportu. Fail-closed (BE-003):

        - (None, None, None) = superuser → queryset bez omezení
        - prázdný rozsah (žádný department ani employer ani vlastník)
          → ``qs.none()``
        - owner_user (student) → přesně jeho vlastní přihlášky
        - jinak filtr departmentu a/nebo employer
        """
        if dept_ids is None and employer is None and owner_user is None:
            return qs
        if not dept_ids and employer is None and owner_user is None:
            return qs.none()
        if owner_user is not None:
            qs = qs.filter(user_id=owner_user.pk)
        if dept_ids:
            qs = qs.filter(practice__subject__department_id__in=dept_ids)
        if employer is not None:
            qs = qs.filter(practice__employer=employer)
        return qs

    @staticmethod
    def get_count(filters: dict, dept_ids: list[int] | None = None, employer=None, owner_user=None) -> int:
        """Vrátí počet záznamů pro dané filtry s role scopingem (prázdný rozsah = 0)."""
        qs = StudentPractice.objects.filter(is_cancelled=False)
        qs = ExportService.apply_scope(qs, dept_ids, employer, owner_user)
        if filters.get("year"):
            qs = qs.filter(year=filters["year"])
        if filters.get("workflow_state") is not None:
            qs = qs.filter(workflow_state=filters["workflow_state"])
        if filters.get("subject_id"):
            qs = qs.filter(practice__subject_id=filters["subject_id"])
        if filters.get("employer_id"):
            qs = qs.filter(practice__employer_id=filters["employer_id"])
        if filters.get("institution"):
            qs = qs.filter(practice__employer__company_name__icontains=filters["institution"])
        return qs.count()

    @staticmethod
    def _export_rows(queryset):
        """Sdílená iterace řádků exportu (XLSX i CSV) včetně sloupce „Garant"."""
        memo = {}
        for sp in queryset.select_related(
            "user",
            "practice",
            "practice__employer",
            "practice__subject",
            "practice__subject__subject_manager",
            "registration",
        ):
            subject_name = ""
            if sp.practice and sp.practice.subject_id:
                try:
                    subject_name = sp.practice.subject.subject_name
                except Exception:
                    pass

            yield [
                _escape_formula_cell(value)
                for value in [
                    sp.student_practice_id,
                    sp.user.full_name if sp.user else "",
                    sp.user.email if sp.user else "",
                    sp.practice.title if sp.practice else "",
                    sp.practice.employer.company_name if sp.practice and sp.practice.employer else "",
                    subject_name,
                    sp.workflow_status_label,
                    str(sp.application_date) if sp.application_date else "",
                    str(sp.practice.start_date) if sp.practice and sp.practice.start_date else "",
                    str(sp.practice.end_date) if sp.practice and sp.practice.end_date else "",
                    sp.hours_completed or 0,
                    _garant_names_for_practice(sp.practice, memo),
                    sp.year or (sp.registration.year if sp.registration_id else "") or "",
                ]
            ]

    @staticmethod
    def generate_xlsx(queryset) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Odborné praxe"

        headers = [
            "ID přihlášky",
            "Student",
            "Email studenta",
            "Praxe",
            "Organizace",
            "Obor / Předmět",
            "Stav workflow",
            "Datum přihlášky",
            "Od",
            "Do",
            "Dokončené hodiny",
            "Garant",
            "Akademický rok",
        ]

        # Style header
        ws.append(headers)
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        for row in ExportService._export_rows(queryset):
            ws.append(row)

        # Auto-adjust column width
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        out = io.BytesIO()
        wb.save(out)
        bytes_data = out.getvalue()
        out.close()
        return bytes_data

    @staticmethod
    def generate_csv(queryset) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "ID přihlášky",
            "Student",
            "Email studenta",
            "Praxe",
            "Organizace",
            "Obor / Předmět",
            "Stav workflow",
            "Datum přihlášky",
            "Od",
            "Do",
            "Dokončené hodiny",
            "Garant",
            "Akademický rok",
        ]
        writer.writerow(headers)

        for row in ExportService._export_rows(queryset):
            writer.writerow(row)

        return output.getvalue()
