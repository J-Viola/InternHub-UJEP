import logging

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _delete_file(field):
    """Delete the physical file referenced by a FileField/ImageField (if any)."""
    if field and field.name:
        try:
            field.delete(save=False)
        except Exception:
            logger.warning("Could not delete file %s", field.name)


# ---------------------------------------------------------------------------
# EmployerProfile
# ---------------------------------------------------------------------------


@receiver(post_delete, sender="users.EmployerProfile")
def delete_employer_logo_on_delete(sender, instance, **kwargs):
    _delete_file(instance.logo)


@receiver(pre_save, sender="users.EmployerProfile")
def delete_employer_logo_on_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.logo and old.logo != instance.logo:
        _delete_file(old.logo)


# ---------------------------------------------------------------------------
# StudentUser
# ---------------------------------------------------------------------------


@receiver(post_delete, sender="users.StudentUser")
def delete_student_files_on_delete(sender, instance, **kwargs):
    _delete_file(instance.profile_picture)
    _delete_file(instance.cv_file)


@receiver(pre_save, sender="users.StudentUser")
def delete_student_files_on_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.profile_picture and old.profile_picture != instance.profile_picture:
        _delete_file(old.profile_picture)
    if old.cv_file and old.cv_file != instance.cv_file:
        _delete_file(old.cv_file)
