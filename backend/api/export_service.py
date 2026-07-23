import csv
import io

import openpyxl
from openpyxl.styles import Font, PatternFill

from student_practices.models import StudentPractice


class ExportService:
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
        ]

        # Style header
        ws.append(headers)
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        for sp in queryset.select_related("user", "practice", "practice__employer"):
            subject_name = ""
            if sp.practice and sp.practice.subject_id:
                try:
                    subject_name = sp.practice.subject.subject_name
                except Exception:
                    pass

            ws.append(
                [
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
                ]
            )

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
        ]
        writer.writerow(headers)

        for sp in queryset.select_related("user", "practice", "practice__employer"):
            subject_name = ""
            if sp.practice and sp.practice.subject_id:
                try:
                    subject_name = sp.practice.subject.subject_name
                except Exception:
                    pass

            writer.writerow(
                [
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
                ]
            )

        return output.getvalue()
