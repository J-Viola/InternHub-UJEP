import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Unicode font pro české znaky (ě/š/č/ř/ž/ů nejsou ve WinAnsi/Helvetica).
# Fallback na Helvetica, pokud font není k dispozici.
_DEJAVU_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_DEJAVU_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _ensure_unicode_fonts():
    registered = pdfmetrics.getRegisteredFontNames()
    if "DejaVu" not in registered:
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", _DEJAVU_PATH))
        except Exception:
            pass
    if "DejaVu-Bold" not in registered:
        try:
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", _DEJAVU_BOLD_PATH))
        except Exception:
            pass


def _font_name(bold: bool = False) -> str:
    if bold and "DejaVu-Bold" in pdfmetrics.getRegisteredFontNames():
        return "DejaVu-Bold"
    if not bold and "DejaVu" in pdfmetrics.getRegisteredFontNames():
        return "DejaVu"
    return "Helvetica-Bold" if bold else "Helvetica"


class PDFEvaluationProtocolGenerator:
    """
    Generates a PDF protocol for a StudentPractice evaluation.
    """

    @staticmethod
    def generate_pdf(evaluation) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            alignment=1,  # Center
            textColor=colors.HexColor("#1E3A8A"),
        )

        normal_style = styles["Normal"]
        bold_style = ParagraphStyle("Bold", parent=normal_style, fontName="Helvetica-Bold")

        story = []

        # Title
        story.append(Paragraph("PROTOKOL O HODNOCENÍ ODBORNÉ PRAXE MENTOREM", title_style))
        story.append(Spacer(1, 15))

        sp = evaluation.student_practice
        student_name = sp.user.full_name if sp and sp.user else "N/A"
        practice_title = sp.practice.title if sp and sp.practice else "N/A"
        employer_name = sp.practice.employer.company_name if sp and sp.practice and sp.practice.employer else "N/A"
        evaluator_name = evaluation.evaluated_by.full_name if evaluation.evaluated_by else "Mentor organizace"
        date_str = evaluation.evaluated_at.strftime("%d. %m. %Y") if evaluation.evaluated_at else ""

        # Metadata Table
        meta_data = [
            [Paragraph("<b>Student:</b>", normal_style), Paragraph(student_name, normal_style)],
            [Paragraph("<b>Praxe:</b>", normal_style), Paragraph(practice_title, normal_style)],
            [Paragraph("<b>Organizace:</b>", normal_style), Paragraph(employer_name, normal_style)],
            [Paragraph("<b>Hodnotitel:</b>", normal_style), Paragraph(evaluator_name, normal_style)],
            [Paragraph("<b>Datum hodnocení:</b>", normal_style), Paragraph(date_str, normal_style)],
        ]

        t_meta = Table(meta_data, colWidths=[120, 400])
        t_meta.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("PADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ]
            )
        )
        story.append(t_meta)
        story.append(Spacer(1, 15))

        # Evaluation Categories Table
        eval_headers = [
            Paragraph("<b>Kategorie</b>", bold_style),
            Paragraph("<b>Hodnocení (1-5)</b>", bold_style),
            Paragraph("<b>Slovní komentář</b>", bold_style),
        ]

        cat_data = [
            eval_headers,
            [
                Paragraph("<b>Odbornost</b>", normal_style),
                Paragraph(f"<b>{evaluation.expertise_rating} / 5</b>", normal_style),
                Paragraph(evaluation.expertise_comment or "—", normal_style),
            ],
            [
                Paragraph("<b>Komunikace</b>", normal_style),
                Paragraph(f"<b>{evaluation.communication_rating} / 5</b>", normal_style),
                Paragraph(evaluation.communication_comment or "—", normal_style),
            ],
            [
                Paragraph("<b>Iniciativa</b>", normal_style),
                Paragraph(f"<b>{evaluation.initiative_rating} / 5</b>", normal_style),
                Paragraph(evaluation.initiative_comment or "—", normal_style),
            ],
        ]

        t_eval = Table(cat_data, colWidths=[110, 100, 310])
        t_eval.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0F2FE")),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ]
            )
        )
        story.append(t_eval)
        story.append(Spacer(1, 15))

        # Overall comment
        if evaluation.overall_comment:
            story.append(Paragraph("<b>Celkové slovní zhodnocení:</b>", bold_style))
            story.append(Spacer(1, 5))
            story.append(Paragraph(evaluation.overall_comment, normal_style))
            story.append(Spacer(1, 20))

        # Hours section
        if evaluation.hours_completed:
            story.append(Paragraph(f"<b>Potvrzený počet hodin:</b> {evaluation.hours_completed}", bold_style))
            story.append(Spacer(1, 20))

        # Footer sign-off
        story.append(Spacer(1, 30))
        sign_data = [
            [
                Paragraph("....................................................", normal_style),
                Paragraph("....................................................", normal_style),
            ],
            [Paragraph("Podpis hodnotitele", normal_style), Paragraph("Razítko organizace", normal_style)],
        ]
        t_sign = Table(sign_data, colWidths=[260, 260])
        t_sign.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(t_sign)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes


class PDFCompletionProtocolGenerator:
    """
    Generuje „Protokol o absolvování odborné praxe".

    Povinné údaje:
    - identifikace studenta (jméno, os. číslo, obor),
    - název firmy,
    - potvrzený počet hodin (``hours_completed``),
    - výsledné hodnocení (Splněno / Nesplněno).

    Pozn: existující ``PDFEvaluationProtocolGenerator`` (mentorský protokol)
    zůstává zachován — tento generátor je určen pro přechod do COMPLETED.
    """

    @staticmethod
    def generate_pdf(student_practice) -> bytes:
        _ensure_unicode_fonts()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            alignment=1,  # Center
            textColor=colors.HexColor("#1E3A8A"),
            fontName=_font_name(bold=True),
        )
        normal_style = ParagraphStyle("NormalDejaVu", parent=styles["Normal"], fontName=_font_name())

        story = []
        story.append(Paragraph("PROTOKOL O ABSOLVOVÁNÍ ODBORNÉ PRAXE", title_style))
        story.append(Spacer(1, 15))

        sp = student_practice
        student = sp.user
        student_name = student.full_name if student else "N/A"
        student_os_cislo = getattr(student, "os_cislo", None) or ""
        student_field = getattr(student, "field_of_study", None) or ""
        employer_name = sp.practice.employer.company_name if sp.practice and sp.practice.employer else "N/A"
        hours = sp.hours_completed or 0
        result = "Splněno" if sp.workflow_state and sp.workflow_state.name == "COMPLETED" else "Nesplněno"

        meta_data = [
            [Paragraph("<b>Student:</b>", normal_style), Paragraph(student_name, normal_style)],
            [Paragraph("<b>Osobní číslo (os. číslo):</b>", normal_style), Paragraph(str(student_os_cislo), normal_style)],
            [Paragraph("<b>Obor:</b>", normal_style), Paragraph(str(student_field), normal_style)],
            [Paragraph("<b>Název firmy:</b>", normal_style), Paragraph(employer_name, normal_style)],
            [Paragraph("<b>Potvrzený počet hodin:</b>", normal_style), Paragraph(str(hours), normal_style)],
            [Paragraph("<b>Výsledné hodnocení:</b>", normal_style), Paragraph(result, normal_style)],
        ]

        t_meta = Table(meta_data, colWidths=[160, 360])
        t_meta.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("PADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ]
            )
        )
        story.append(t_meta)
        story.append(Spacer(1, 30))

        sign_data = [
            [
                Paragraph("....................................................", normal_style),
                Paragraph("....................................................", normal_style),
            ],
            [Paragraph("Podpis garanta", normal_style), Paragraph("Razítko katedry", normal_style)],
        ]
        t_sign = Table(sign_data, colWidths=[260, 260])
        t_sign.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(t_sign)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
