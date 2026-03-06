import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _delete_file(field):
    if field and field.name:
        try:
            field.delete(save=False)
        except Exception:
            logger.warning("Could not delete document %s", field.name)


@receiver(post_delete, sender="student_practices.UploadedDocument")
def delete_document_on_delete(sender, instance, **kwargs):
    _delete_file(instance.document)
