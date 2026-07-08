"""
Generates practice evaluation/feedback documents (Hodnocení odborné praxe).
"""

import io

from docx import Document
from docx.shared import Pt


class FeedbackGenerator:
    """Generates a practice evaluation form (Hodnocení odborné praxe)."""

    @staticmethod
    def generate(student_name: str, practice_title: str) -> io.BytesIO:
        doc = Document()
        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(11)

        doc.add_heading("Hodnocení odborné praxe", level=1)
        doc.add_paragraph(f"Student: {student_name}")
        doc.add_paragraph(f"Praxe: {practice_title}")

        doc.add_heading("Hodnocení studenta poskytovatelem praxe", level=2)
        doc.add_paragraph("Odborné znalosti:     □ výborné  □ dobré  □ dostatečné  □ nedostatečné")
        doc.add_paragraph("Pracovní nasazení:    □ výborné  □ dobré  □ dostatečné  □ nedostatečné")
        doc.add_paragraph("Samostatnost:         □ výborná  □ dobrá  □ dostatečná  □ nedostatečná")
        doc.add_paragraph("Komunikační dovednosti: □ výborné  □ dobré  □ dostatečné  □ nedostatečné")

        doc.add_heading("Slovní hodnocení:", level=2)
        for _ in range(5):
            doc.add_paragraph("_" * 80)

        doc.add_heading("Vyjádření studenta:", level=2)
        for _ in range(3):
            doc.add_paragraph("_" * 80)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
