import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import DatabaseError, IntegrityError

from users.models import ApprovalStatus

from .models import Notification, NotificationType

logger = logging.getLogger(__name__)


class EmailService:
    """
    All domain-specific email methods remain here.
    NotificationService handles only in-app notifications.
    """

    @staticmethod
    def _send_email(subject, message, recipient_list):
        if not recipient_list:
            return
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    @staticmethod
    def notify_org_new_application(student_practice):
        """
        Notify organization contact user about a new student application.
        """
        practice = student_practice.practice
        student = student_practice.user
        org_contact = practice.contact_user

        if org_contact and org_contact.email:
            subject = f"Nová přihláška na praxi: {practice.title}"
            message = (
                f"Dobrý den,\n\n"
                f"student {student.full_name} ({student.email}) "
                f"se přihlásil na Vaši praxi '{practice.title}'.\n\n"
                f"Přihlášku můžete spravovat v systému InternHub.\n\n"
                f"Tým InternHub"
            )
            EmailService._send_email(subject, message, [org_contact.email])

    @staticmethod
    def notify_student_application_status(student_practice):
        """
        Notify student when their application status changes to Approved or Rejected.
        """
        student = student_practice.user
        practice = student_practice.practice
        status = student_practice.approval_status

        if not student or not student.email:
            return

        if status == ApprovalStatus.APPROVED:
            status_text = "schválena"
        elif status == ApprovalStatus.REJECTED:
            status_text = "zamítnuta"
        else:
            return  # Only notify on final statuses

        subject = f"Stav Vaší přihlášky na praxi: {status_text.capitalize()}"
        message = (
            f"Dobrý den,\n\n"
            f"Vaše přihláška na praxi '{practice.title}' byla {status_text}.\n\n"
            f"Více informací naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [student.email])

    @staticmethod
    def notify_org_practice_status(practice):
        """
        Notify organization when their practice offer is approved or rejected by the school.
        """
        org_contact = practice.contact_user
        status = practice.approval_status

        if not org_contact or not org_contact.email:
            return

        if status == ApprovalStatus.APPROVED:
            status_text = "schválena"
        elif status == ApprovalStatus.REJECTED:
            status_text = "zamítnuta"
        else:
            return  # Only notify on final statuses

        subject = f"Stav Vaší nabídky praxe: {status_text.capitalize()}"
        message = f"Dobrý den,\n\n" f"Vaše nabídka praxe '{practice.title}' byla školou {status_text}.\n\n" f"Tým InternHub"
        EmailService._send_email(subject, message, [org_contact.email])

    @staticmethod
    def notify_student_document_review(document):
        """
        Notify student when their document is approved or rejected.
        """
        from student_practices.models import DocumentStatus

        student_practice = document.student_practice
        if not student_practice or not student_practice.user or not student_practice.user.email:
            return

        status_text = "schválen" if document.status == DocumentStatus.APPROVED else "zamítnut"
        subject = f"Dokument k praxi byl {status_text}"

        message = (
            f"Dobrý den,\n\n"
            f"Váš dokument '{document.document_type.name.lower()}' k praxi '{student_practice.practice.title}' "
            f"byl vyučujícím {status_text}.\n"
        )

        if document.status == DocumentStatus.REJECTED and document.review_note:
            message += f"\nDůvod zamítnutí: {document.review_note}\n"

        message += "\nVíce informací naleznete v systému InternHub.\n\nTým InternHub"

        EmailService._send_email(subject, message, [student_practice.user.email])

    @staticmethod
    def notify_professors_document_upload(document):
        """
        Notify relevant professors when a student uploads a document.
        """
        student_practice = document.student_practice
        if not student_practice:
            return

        subject_obj = student_practice.practice.subject
        if not subject_obj:
            return

        # Get all professors assigned to this subject
        from users.models import UserSubjectType

        recipient_emails = list(
            subject_obj.user_subjects.filter(role=UserSubjectType.Professor, user__email__isnull=False).values_list(
                "user__email", flat=True
            )
        )

        # Also add subject manager if not already in list
        if subject_obj.subject_manager and subject_obj.subject_manager.email:
            if subject_obj.subject_manager.email not in recipient_emails:
                recipient_emails.append(subject_obj.subject_manager.email)

        if not recipient_emails:
            return

        student = student_practice.user
        subject = f"Nový dokument k posouzení: {student.full_name}"
        message = (
            f"Dobrý den,\n\n"
            f"student {student.full_name} nahrál nový dokument '{document.document_type.name.lower()}' "
            f"k praxi '{student_practice.practice.title}' v rámci předmětu {subject_obj.subject_name}.\n\n"
            f"Dokument prosím zkontrolujte v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, recipient_emails)

    @staticmethod
    def notify_student_invitation(invitation):
        """
        Notify student about a new invitation from an employer.
        """
        student = invitation.user
        practice = invitation.practice
        employer = invitation.employer

        if not student or not student.email:
            return

        subject = f"Pozvánka na praxi: {practice.title}"
        message = (
            f"Dobrý den,\n\n"
            f"Organizace {employer.company_name} Vás pozvala k účasti na praxi '{practice.title}'.\n\n"
            f"Zprávu od organizace a detaily praxe naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [student.email])

    @staticmethod
    def notify_password_reset(user, reset_url):
        """
        Send password reset link to user.
        """
        if not user or not user.email:
            return

        subject = "Obnova hesla - InternHub UJEP"
        message = (
            f"Dobrý den,\n\n"
            f"pro obnovu hesla v systému InternHub klikněte na tento odkaz:\n"
            f"{reset_url}\n\n"
            f"Pokud jste o obnovu nežádali, tento email ignorujte.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [user.email])

    @staticmethod
    def notify_password_changed(user):
        """
        Notify user that their password was successfully changed.
        """
        if not user or not user.email:
            return

        subject = "Vaše heslo bylo změněno - InternHub UJEP"
        message = (
            "Dobrý den,\n\n"
            "Vaše heslo do systému InternHub bylo úspěšně změněno.\n"
            "Pokud jste tuto akci neprovedli, okamžitě kontaktujte podporu.\n\n"
            "Tým InternHub"
        )
        EmailService._send_email(subject, message, [user.email])

    @staticmethod
    def notify_org_welcome(user):
        """
        Send welcome email to a newly registered organization user.
        """
        if not user or not user.email:
            return

        subject = "Vítejte v InternHub UJEP"
        message = (
            "Dobrý den,\n\n"
            "Vaše registrace do systému InternHub proběhla úspěšně.\n"
            "Jakmile bude Váš profil organizace schválen administrátorem, "
            "budete moci začít vkládat nabídky praxí.\n\n"
            "Tým InternHub"
        )
        EmailService._send_email(subject, message, [user.email])

    @staticmethod
    def notify_org_profile_status(employer_profile):
        """
        Notify organization owner when their profile is approved or rejected.
        """
        # Find owner email
        from users.models import OrganizationRole

        owner = employer_profile.organization_users.filter(organization_role=OrganizationRole.OWNER).first()

        if not owner or not owner.email:
            return

        status = employer_profile.approval_status
        if status == ApprovalStatus.APPROVED:
            status_text = "schválen"
        elif status == ApprovalStatus.REJECTED:
            status_text = "zamítnut"
        else:
            return

        subject = f"Stav Vašeho profilu organizace: {status_text.capitalize()}"
        message = f"Dobrý den,\n\n" f"Váš profil organizace '{employer_profile.company_name}' byl administrátorem {status_text}.\n"

        if status == ApprovalStatus.APPROVED:
            message += "Nyní můžete začít vkládat nabídky praxí do systému.\n"

        message += "\nTým InternHub"
        EmailService._send_email(subject, message, [owner.email])

    @staticmethod
    def notify_student_cancellation(user, student_practice, reason):
        """
        Notify student that their StudentPractice was canceled.
        """
        if not user or not user.email:
            return

        practice_title = student_practice.practice.title if student_practice.practice else "N/A"
        subject = "Vaše přihláška na praxi byla zrušena"
        message = (
            f"Dobrý den,\n\n"
            f"Vaše přihláška na praxi '{practice_title}' byla zrušena.\n"
            f"Důvod: {reason}\n\n"
            f"Více informací naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [user.email])

    @staticmethod
    def notify_org_cancellation(employer, student_practice, reason):
        """
        Notify organization contact that a StudentPractice was cancelled.

        Args:
            employer: EmployerProfile instance
            student_practice: StudentPractice instance
            reason: Cancellation reason string
        """
        practice = student_practice.practice
        org_contact = practice.contact_user if practice else None

        if not org_contact or not org_contact.email:
            return

        student_name = student_practice.user.full_name if student_practice.user else "N/A"
        practice_title = practice.title if practice else "N/A"

        subject = "Přihláška studenta na praxi byla zrušena"
        message = (
            f"Dobrý den,\n\n"
            f"Přihláška studenta {student_name} na praxi '{practice_title}' "
            f"byla zrušena.\n"
            f"Důvod: {reason}\n\n"
            f"Více informací naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [org_contact.email])

    @staticmethod
    def notify_admins_new_org_registration(organization_user):
        """
        Notify all admin/superuser users about a new organization registration.
        """
        from users.models import User

        admin_emails = list(User.objects.filter(is_superuser=True, email__isnull=False).exclude(email="").values_list("email", flat=True))

        if not admin_emails:
            return

        org_name = (
            organization_user.employer_profile.company_name
            if hasattr(organization_user, "employer_profile") and organization_user.employer_profile
            else organization_user.email
        )

        subject = f"Nová registrace organizace: {org_name}"
        message = (
            f"Dobrý den,\n\n"
            f"Do systému InternHub se zaregistrovala nová organizace:\n\n"
            f"Název: {org_name}\n"
            f"Email: {organization_user.email}\n\n"
            f"Profil organizace čeká na schválení v administraci.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, admin_emails)


class NotificationService:
    """In-app notification service (WP5).

    Creates Notification model instances for display in the notification bell + page.
    By default does NOT send email — emails remain in EmailService (per 5.4a strategy).
    """

    @staticmethod
    def create_notification(
        recipient,
        verb,
        message,
        actor=None,
        target=None,
        notification_type=NotificationType.INFO,
        send_email=False,
    ):
        """
        Create an in-app notification. Optionally sends email when send_email=True.

        Args:
            recipient: User object (required) — who receives the notification.
            verb: Machine event name, e.g. 'PRACTICE_APPROVED'.
            message: Human-readable notification text (Czech).
            actor: User who performed the action (optional, None = system event).
            target: Any model instance — stored via GenericFK (optional).
            notification_type: Severity enum (default INFO).
            send_email: Whether to also send an email (default False per 5.4a).
        """
        try:
            notification_data = {
                "recipient": recipient,
                "actor": actor,
                "verb": verb,
                "message": message,
                "notification_type": notification_type,
            }

            if target is not None:
                notification_data["target"] = target

            notification = Notification.objects.create(**notification_data)

            if send_email and recipient.email:
                NotificationService._send_email(recipient, verb, message)

            return notification
        except (DatabaseError, IntegrityError) as e:
            logger.exception(f"Failed to create notification for {recipient}: {str(e)}")
            raise

    @staticmethod
    def _send_email(recipient, verb, message):
        """Internal: send a simple email notification for a notification event."""
        subject = f"InternHub: {verb.replace('_', ' ').title()}"
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send email to {recipient.email}: {str(e)}")
