"""
Generates practice report/log documents (Výkaz odborné praxe).
"""

import io

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


class ReportGenerator:
    """Generates a practice report/log (Výkaz odborné praxe) document."""

    @staticmethod
    def generate(student_name: str, practice_title: str, start_date: str, end_date: str, hours: int) -> io.BytesIO:
        doc = Document()
        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(11)

        doc.add_heading("Výkaz odborné praxe", level=1)
        doc.add_paragraph(f"Student: {student_name}")
        doc.add_paragraph(f"Praxe: {practice_title}")
        doc.add_paragraph(f"Období: {start_date} – {end_date}")
        doc.add_paragraph(f"Počet hodin: {hours}")

        doc.add_heading("Záznam o průběhu praxe", level=2)

        table = doc.add_table(rows=11, cols=4)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        headers = ["Datum", "Počet hodin", "Popis činnosti", "Podpis konzultanta"]
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = header
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(9)
                    run.bold = True

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
