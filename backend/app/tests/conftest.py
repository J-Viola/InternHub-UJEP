import pytest
from docx import Document


def _write_minimal_docx(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Document().save(path)


@pytest.fixture(autouse=True)
def test_media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    default_documents = settings.MEDIA_ROOT / "default_documents"
    for filename in ("default_contract.docx", "default_content.docx", "default_feedback.docx"):
        _write_minimal_docx(default_documents / filename)
