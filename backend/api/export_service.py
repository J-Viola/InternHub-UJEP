import csv
import io

import openpyxl
from openpyxl.styles import Font, PatternFill

from student_practices.models import StudentPractice


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
        Vrátí (dept_ids, employer) pro role-based scoping exportu.

        - superuser → bez omezení (dept_ids=None, employer=None)
        - garant / profesor katedry → jen praxe svého departmentu
          (practice.subject.department); primárně user.department,
          doplňkově departmenty z user_subjects
        - organizace → jen praxe vlastní employer_profile
        """
        dept_ids = None
        employer = None

        if user is None or user.is_superuser:
            return dept_ids, employer

        from users.models import ProfessorUser, StudentUser

        if isinstance(user, ProfessorUser):
            dept_ids = []
            if user.department_id:
                dept_ids.append(user.department_id)
            # Fallback: departmenty, na kterých uživatel učí
            if hasattr(user, "user_subjects"):
                dept_ids.extend(user.user_subjects.values_list("subject__department_id", flat=True).distinct())
            dept_ids = list(dict.fromkeys(d for d in dept_ids if d))
        elif isinstance(user, StudentUser):
            # Studenti vidí jen praxe svých předmětů (konzervativní výchozí chování)
            if hasattr(user, "user_subjects"):
                dept_ids = list(user.user_subjects.values_list("subject__department_id", flat=True).distinct())

        if hasattr(user, "employer_profile") and user.employer_profile:
            employer = user.employer_profile

        return dept_ids, employer

    @staticmethod
    def get_count(filters: dict, dept_ids: list[int] | None = None, employer=None) -> int:
        """Vrátí počet záznamů pro dané filtry s volitelným department/employer scopingem."""
        qs = StudentPractice.objects.filter(is_cancelled=False)
        if dept_ids:
            qs = qs.filter(practice__subject__department_id__in=dept_ids)
        if employer is not None:
            qs = qs.filter(practice__employer=employer)
        if filters.get("year"):
            qs = qs.filter(year=filters["year"])
        if filters.get("workflow_state") is not None:
            qs = qs.filter(workflow_state=filters["workflow_state"])
        if filters.get("subject_id"):
            qs = qs.filter(practice__subject_id=filters["subject_id"])
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
        ):
            subject_name = ""
            if sp.practice and sp.practice.subject_id:
                try:
                    subject_name = sp.practice.subject.subject_name
                except Exception:
                    pass

            yield [
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
            ]

    @staticmethod
    def generate_xlsx(queryset) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Odborné praxe"

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
        writer.writerow(headers)

        for row in ExportService._export_rows(queryset):
            writer.writerow(row)

        return output.getvalue()
