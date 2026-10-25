"""A-11 — pomocníci pro testy, které potřebují schválený smluvní dokument.

Do ``CONTRACTED`` se nejde bez schváleného smluvního dokumentu (žádný override),
testy proto před přechodem dokument schválí tímto helperem.
"""

import io

from docx import Document


def make_valid_docx_bytes() -> bytes:
    """Platné DOCX (obsahuje ``word/``), které projde ``validate_file_content``."""
    buf = io.BytesIO()
    Document().save(buf)
    return buf.getvalue()


def approve_contract_document(sp):
    """Zajistí u přihlášky schválený smluvní dokument (vytvoří záznam, pokud chybí)."""
    from student_practices.models import DocumentStatus, DocumentType, UploadedDocument

    doc = sp.contract_document
    if doc is None:
        doc = UploadedDocument.objects.create(document_type=DocumentType.CONTRACT, status=DocumentStatus.APPROVED)
        sp.contract_document = doc
        sp.save(update_fields=["contract_document"])
    elif doc.status != DocumentStatus.APPROVED:
        doc.status = DocumentStatus.APPROVED
        doc.save(update_fields=["status"])
    return sp
