"""
Generates work content description documents (Pracovní náplň).
"""

import io

from docx import Document
from docx.shared import Pt


class ContentGenerator:
    """Generates a work content description (Pracovní náplň) document."""

    @staticmethod
    def generate(title: str, description: str, responsibilities: str, hours: int) -> io.BytesIO:
        doc = Document()
        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(11)

        doc.add_heading("Pracovní náplň odborné praxe", level=1)
        doc.add_paragraph(f"Název praxe: {title}")
        doc.add_paragraph(f"Rozsah: {hours} hodin")
        doc.add_heading("Popis činností:", level=2)
        doc.add_paragraph(description or "Není specifikováno.")
        doc.add_heading("Konkrétní odpovědnosti:", level=2)
        doc.add_paragraph(responsibilities or "Není specifikováno.")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
