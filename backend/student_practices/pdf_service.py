import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class PDFEvaluationProtocolGenerator:
    """
    Generates a PDF protocol for a StudentPractice evaluation (RF-10 / Item 2.12).
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
