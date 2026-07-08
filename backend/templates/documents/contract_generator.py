"""
Generates Czech internship contract documents using python-docx.
"""

import io
from datetime import date

from django.conf import settings
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt


class ContractGenerator:
    """
    Generates a Czech internship contract (Smlouva o zajištění odborné praxe)
    as a .docx document.
    """

    @staticmethod
    def generate(
        student_name: str,
        student_birth_date: str,
        student_birth_place: str,
        student_address: str,
        student_email: str,
        student_phone: str,
        student_os_cislo: str,
        student_field: str,
        student_year: int,
        employer_name: str,
        employer_address: str,
        employer_ico: str,
        employer_contact: str,
        employer_email: str,
        practice_title: str,
        practice_description: str,
        practice_start_date: str,
        practice_end_date: str,
        practice_hours: int,
        subject_name: str,
        subject_code: str,
        supervisor_name: str | None = None,
        garant_name: str | None = None,
    ) -> io.BytesIO:
        """
        Generate a complete Czech internship contract.

        Returns:
            io.BytesIO containing the .docx document ready for download.
        """
        doc = Document()

        # Page margins
        for section in doc.sections:
            section.top_margin = Cm(2.5)
            section.bottom_margin = Cm(2.5)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(11)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.line_spacing = 1.15

        # ============= HEADER =============
        header_para = doc.add_paragraph()
        header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = header_para.add_run("SMLOUVA O ZAJIŠTĚNÍ ODBORNÉ PRAXE")
        run.bold = True
        run.font.size = Pt(14)

        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = subtitle.add_run("uzavřená podle § 1746 odst. 2 zákona č. 89/2012 Sb., občanský zákoník")
        run.font.size = Pt(10)
        run.italic = True

        doc.add_paragraph()  # spacing

        # ============= PARTIES =============
        # University
        h = doc.add_paragraph()
        run = h.add_run("Smluvní strany:")
        run.bold = True

        p1 = doc.add_paragraph()
        p1.paragraph_format.space_after = Pt(2)
        run = p1.add_run(f"1. {settings.UNIVERSITY_NAME}")
        run.bold = True
        p1.add_run(f"\nse sídlem: {settings.UNIVERSITY_ADDRESS}")
        p1.add_run(f"\nIČO: {settings.UNIVERSITY_ICO}")
        p1.add_run("\nzastoupená: ")
        if garant_name:
            p1.add_run(f"{garant_name}")
        else:
            p1.add_run("garantem příslušné katedry")
        p1.add_run("\n(dále jen „škola“)")

        # Student
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_after = Pt(2)
        run = p2.add_run(f"2. {student_name}")
        run.bold = True
        if student_birth_date:
            p2.add_run(f"\nnar.: {student_birth_date}")
        if student_birth_place:
            p2.add_run(f", {student_birth_place}")
        if student_address:
            p2.add_run(f"\nbydliště: {student_address}")
        p2.add_run(f"\ne-mail: {student_email}")
        if student_phone:
            p2.add_run(f", tel.: {student_phone}")
        p2.add_run(f"\nosobní číslo: {student_os_cislo}")
        if student_field:
            p2.add_run(f"\nobor: {student_field}, {student_year}. ročník")
        p2.add_run("\n(dále jen „student“)")

        # Employer
        p3 = doc.add_paragraph()
        p3.paragraph_format.space_after = Pt(2)
        run = p3.add_run(f"3. {employer_name}")
        run.bold = True
        if employer_address:
            p3.add_run(f"\nse sídlem: {employer_address}")
        if employer_ico:
            p3.add_run(f"\nIČO: {employer_ico}")
        if employer_contact:
            p3.add_run(f"\nkontaktní osoba: {employer_contact}")
        if employer_email:
            p3.add_run(f", e-mail: {employer_email}")
        p3.add_run("\n(dále jen „poskytovatel praxe“)")

        doc.add_paragraph()

        # ============= ARTICLE I — Subject =============
        h = doc.add_paragraph()
        run = h.add_run("I. Předmět smlouvy")
        run.bold = True
        run.font.size = Pt(12)

        p = doc.add_paragraph()
        p.add_run(
            "Předmětem této smlouvy je závazek poskytovatele praxe umožnit studentovi " "výkon odborné praxe v rámci studijního programu "
        )
        if student_field:
            p.add_run(f"{student_field}")
        else:
            p.add_run("studenta")
        p.add_run(f" na {settings.UNIVERSITY_NAME} (dále jen „UJEP“), " "a to za podmínek stanovených touto smlouvou.")

        # ============= ARTICLE II — Practice details =============
        h = doc.add_paragraph()
        run = h.add_run("II. Rozsah a místo výkonu praxe")
        run.bold = True
        run.font.size = Pt(12)

        p = doc.add_paragraph()
        p.add_run("Název praxe: ")
        run = p.add_run(f"{practice_title}")
        run.bold = True

        p = doc.add_paragraph()
        p.add_run(f"Předmět: {subject_name} ({subject_code})")

        p = doc.add_paragraph()
        p.add_run(f"Období: {practice_start_date} – {practice_end_date}")

        p = doc.add_paragraph()
        p.add_run(f"Rozsah praxe: {practice_hours} hodin")

        p = doc.add_paragraph()
        p.add_run("Náplň práce:")
        if practice_description:
            p2 = doc.add_paragraph()
            p2.paragraph_format.left_indent = Cm(1)
            p2.add_run(practice_description)

        # ============= ARTICLE III — Obligations =============
        h = doc.add_paragraph()
        run = h.add_run("III. Práva a povinnosti smluvních stran")
        run.bold = True
        run.font.size = Pt(12)

        p = doc.add_paragraph()
        run = p.add_run("1. Poskytovatel praxe se zavazuje:")
        run.bold = True
        doc.add_paragraph("a) umožnit studentovi výkon odborné praxe v dohodnutém rozsahu,", style="List Bullet")
        doc.add_paragraph("b) seznámit studenta s předpisy BOZP a požární ochrany před zahájením praxe,", style="List Bullet")
        doc.add_paragraph("c) poskytnout studentovi potřebné pracovní vybavení a prostředky,", style="List Bullet")
        doc.add_paragraph("d) určit odborného konzultanta, který bude praxi studenta vést,", style="List Bullet")
        doc.add_paragraph("e) potvrdit studentovi absolvování praxe.", style="List Bullet")

        p = doc.add_paragraph()
        run = p.add_run("2. Student se zavazuje:")
        run.bold = True
        doc.add_paragraph("a) absolvovat odbornou praxi v dohodnutém rozsahu a termínu,", style="List Bullet")
        doc.add_paragraph("b) dodržovat předpisy BOZP a požární ochrany,", style="List Bullet")
        doc.add_paragraph("c) řídit se pokyny odborného konzultanta poskytovatele praxe,", style="List Bullet")
        doc.add_paragraph("d) zachovávat mlčenlivost o skutečnostech, se kterými se seznámí při výkonu praxe,", style="List Bullet")
        doc.add_paragraph("e) vést evidenci vykonané praxe a předložit ji ke kontrole.", style="List Bullet")

        p = doc.add_paragraph()
        run = p.add_run("3. Škola se zavazuje:")
        run.bold = True
        doc.add_paragraph("a) poskytnout studentovi a poskytovateli praxe metodickou podporu,", style="List Bullet")
        doc.add_paragraph("b) jmenovat garanta odborné praxe, který dohlíží na její průběh,", style="List Bullet")
        doc.add_paragraph("c) na základě potvrzení o absolvování udělit studentovi zápočet.", style="List Bullet")

        # ============= ARTICLE IV — Financial =============
        h = doc.add_paragraph()
        run = h.add_run("IV. Finanční ujednání")
        run.bold = True
        run.font.size = Pt(12)

        doc.add_paragraph(
            "Odborná praxe je vykonávána bez nároku na odměnu od poskytovatele praxe, "
            "není-li mezi studentem a poskytovatelem praxe sjednáno jinak. "
            "Škola nehradí poskytovateli praxe žádné náklady spojené s výkonem praxe."
        )

        # ============= ARTICLE V — Duration =============
        h = doc.add_paragraph()
        run = h.add_run("V. Doba trvání smlouvy")
        run.bold = True
        run.font.size = Pt(12)

        doc.add_paragraph(f"Tato smlouva se uzavírá na dobu určitou, a to od {practice_start_date} do {practice_end_date}.")
        doc.add_paragraph(
            "Smlouvu lze ukončit písemnou dohodou smluvních stran nebo písemnou výpovědí "
            "kterékoli smluvní strany s výpovědní lhůtou 14 dnů, která počíná běžet dnem "
            "doručení výpovědi druhé smluvní straně."
        )

        # ============= ARTICLE VI — Final provisions =============
        h = doc.add_paragraph()
        run = h.add_run("VI. Závěrečná ustanovení")
        run.bold = True
        run.font.size = Pt(12)

        doc.add_paragraph("1. Tato smlouva nabývá platnosti a účinnosti dnem podpisu všemi smluvními stranami.")
        doc.add_paragraph("2. Smlouva je vyhotovena ve třech stejnopisech, z nichž každá smluvní strana obdrží jedno vyhotovení.")
        doc.add_paragraph(
            "3. Smluvní strany prohlašují, že si tuto smlouvu přečetly, "
            "že s jejím obsahem souhlasí a že byla sepsána na základě jejich pravé a svobodné vůle, "
            "což stvrzují svými podpisy."
        )

        doc.add_paragraph()
        doc.add_paragraph()

        # ============= SIGNATURES =============
        # Create a signature table
        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        # Headers
        for i, text in enumerate(["Za školu:", "Za studenta:", "Za poskytovatele praxe:"]):
            cell = table.rows[0].cells[i]
            cell.text = text
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(10)
                    run.bold = True

        # Add empty rows for signatures
        for _ in range(4):
            table.add_row()

        # Date row
        today = date.today().strftime("%d. %m. %Y")
        footer_text = f"\nV Ústí nad Labem dne {today}"

        footer_para = doc.add_paragraph()
        footer_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        footer_para.add_run(footer_text)

        # Save to BytesIO
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return buffer
