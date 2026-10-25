import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string

from api.parameter_service import get_param
from users.models import ApprovalStatus

from .models import Notification, NotificationType

logger = logging.getLogger(__name__)


class EmailService:
    """
    All domain-specific email methods remain here.
    NotificationService handles only in-app notifications.
    """

    @staticmethod
    def _send_email(subject, message, recipient_list, html_message=None):
        if not recipient_list:
            return
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
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
        try:
            html_message = render_to_string(
                "notifications/application_status.html",
                {
                    "practice_title": practice.title if practice else "",
                    "is_approved": status == ApprovalStatus.APPROVED,
                    "status_text": status_text,
                    "rejection_reason": getattr(student_practice, "rejection_reason", ""),
                    "site_url": getattr(settings, "SITE_URL", "http://localhost:3000"),
                },
            )
        except Exception as t_err:
            logger.warning(f"Failed to render application_status HTML template: {t_err}")
            html_message = None

        EmailService._send_email(subject, message, [student.email], html_message=html_message)

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

    # ------------------------------------------------------------------
    # 1.11: Notifications for 6 new workflow states
    # ------------------------------------------------------------------

    @staticmethod
    def notify_student_awaiting_contract(student_practice):
        """
        Notify student that the contract preparation has started (AWAITING_CONTRACT).
        """
        student = student_practice.user
        if not student or not student.email:
            return

        practice_title = student_practice.practice.title if student_practice.practice else "N/A"
        subject = f"Příprava smlouvy - {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"byla zahájena příprava smlouvy k praxi '{practice_title}'.\n\n"
            f"Jakmile bude smlouva připravena, budete informováni.\n\n"
            f"Více informací naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        html_message = None
        try:
            html_message = render_to_string(
                "notifications/application_status.html",
                {
                    "practice_title": practice_title,
                    "is_approved": True,
                    "status_text": "čeká na smlouvu",
                    "rejection_reason": "",
                    "site_url": getattr(settings, "SITE_URL", "http://localhost:3000"),
                },
            )
        except Exception as t_err:
            logger.warning(f"Failed to render awaiting_contract HTML template: {t_err}")
        EmailService._send_email(subject, message, [student.email], html_message=html_message)

    @staticmethod
    def notify_student_awaiting_documents(student_practice):
        """
        Notify student that documents are required (AWAITING_DOCUMENTS).
        """
        student = student_practice.user
        if not student or not student.email:
            return

        practice_title = student_practice.practice.title if student_practice.practice else "N/A"
        subject = f"Žádost o nahrání dokumentů - {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"žádáme Vás o nahrání požadovaných dokumentů k praxi '{practice_title}'.\n\n"
            f"Prosím nahrajte dokumenty co nejdříve v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [student.email])

    @staticmethod
    def notify_student_documents_rejected(student_practice, reason):
        """
        Notify student that their documents were rejected (DOCUMENTS_REJECTED).
        """
        student = student_practice.user
        if not student or not student.email:
            return

        practice_title = student_practice.practice.title if student_practice.practice else "N/A"
        subject = f"Dokumenty zamítnuty - {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"Vaše dokumenty k praxi '{practice_title}' byly zamítnuty.\n"
            f"Důvod: {reason}\n\n"
            f"Prosím nahrajte opravené dokumenty v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [student.email])

    @staticmethod
    def notify_professor_content_approval(student_practice):
        """
        Notify professor/garant that content awaits approval (AWAITING_CONTENT_APPROVAL).
        """
        practice = student_practice.practice
        subject_obj = practice.subject if practice else None
        if not subject_obj or not subject_obj.subject_manager or not subject_obj.subject_manager.email:
            return

        student = student_practice.user
        student_name = student.full_name if student else "N/A"
        practice_title = practice.title if practice else "N/A"
        subject = f"Obsah praxe ke schválení - {student_name}"
        message = (
            f"Dobrý den,\n\n"
            f"student {student_name} odeslal obsah praxe '{practice_title}' ke schválení.\n\n"
            f"Prosím zkontrolujte a schvalte obsah v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [subject_obj.subject_manager.email])

    @staticmethod
    def notify_student_content_rejected(student_practice, reason):
        """
        Notify student that the content was rejected (CONTENT_REJECTED).
        """
        student = student_practice.user
        if not student or not student.email:
            return

        practice_title = student_practice.practice.title if student_practice.practice else "N/A"
        subject = f"Obsah praxe zamítnut - {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"obsah praxe '{practice_title}' byl zamítnut garantem.\n"
            f"Důvod: {reason}\n\n"
            f"Prosím opravte obsah a odešlete znovu v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [student.email])

    @staticmethod
    def notify_student_content_approved(student_practice):
        """
        Notify student that the content was approved (CONTENT_APPROVED).
        """
        student = student_practice.user
        if not student or not student.email:
            return

        practice_title = student_practice.practice.title if student_practice.practice else "N/A"
        subject = f"Obsah praxe schválen - {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"obsah praxe '{practice_title}' byl schválen garantem.\n\n"
            f"Více informací naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, [student.email])

    # ------------------------------------------------------------------
    # Nové e-maily garantům
    # Příjemci garantů se řeší přes NotificationService.resolve_garant_recipients.
    # ------------------------------------------------------------------

    @staticmethod
    def _garant_emails(practice_or_sp):
        """Vyřeší e-maily garantů (prázdný list, pokud žádný)."""
        recipients = NotificationService.resolve_garant_recipients(practice_or_sp)
        return [u.email for u in recipients if getattr(u, "email", "")]

    @staticmethod
    def notify_garant_new_application_email(student_practice):
        """E-mail garantům: nová žádost o praxi (verb NEW_APPLICATION_GARANT)."""
        recipient_emails = EmailService._garant_emails(student_practice)
        if not recipient_emails:
            return
        practice = student_practice.practice
        student = student_practice.user
        practice_title = practice.title if practice else "N/A"
        student_name = student.full_name if student else "N/A"
        subject = f"Nová přihláška na praxi: {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"student {student_name} ({student.email}) se přihlásil na praxi "
            f"'{practice_title}'.\n\n"
            f"Žádost prosím posuďte v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, recipient_emails)

    @staticmethod
    def notify_garant_cancellation_email(student_practice):
        """E-mail garantům: student zrušil přihlášku (verb CANCELLATION_GARANT)."""
        recipient_emails = EmailService._garant_emails(student_practice)
        if not recipient_emails:
            return
        practice = student_practice.practice
        student = student_practice.user
        practice_title = practice.title if practice else "N/A"
        student_name = student.full_name if student else "N/A"
        subject = f"Storno přihlášky na praxi: {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"student {student_name} zrušil svou přihlášku na praxi '{practice_title}'.\n\n"
            f"Detaily naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, recipient_emails)

    @staticmethod
    def notify_garant_evaluation_submitted_email(evaluation):
        """E-mail garantům: mentor odeslal evaluaci (verb EVALUATION_SUBMITTED)."""
        student_practice = evaluation.student_practice
        if not student_practice:
            return
        recipient_emails = EmailService._garant_emails(student_practice)
        if not recipient_emails:
            return
        practice = student_practice.practice
        student = student_practice.user
        practice_title = practice.title if practice else "N/A"
        student_name = student.full_name if student else "N/A"
        subject = f"Evaluace k praxi: {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"mentor odeslal evaluaci k praxi '{practice_title}' studenta {student_name}.\n\n"
            f"Hodnocení naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, recipient_emails)

    @staticmethod
    def notify_org_allocation_email(student_practice):
        """
        E-mail organizaci: praxe přešla do CONTRACTED (verb ALLOCATION_ORG).

        Adresáti: ``practice.contact_user`` + owner EmployerProfile (pokud se liší).
        """
        practice = student_practice.practice
        if not practice:
            return

        from users.models import OrganizationRole

        recipient_emails = []
        contact_user = practice.contact_user
        if contact_user and contact_user.email:
            recipient_emails.append(contact_user.email)

        if practice.employer:
            owner = practice.employer.organization_users.filter(organization_role=OrganizationRole.OWNER).first()
            if owner and owner.email and owner.email not in recipient_emails:
                recipient_emails.append(owner.email)

        if not recipient_emails:
            return

        student = student_practice.user
        practice_title = practice.title or "N/A"
        student_name = student.full_name if student else "N/A"
        subject = f"Alokace praxe: {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"praxe '{practice_title}' byla alokována studentovi {student_name} "
            f"a přešla do stavu 'Zasmluvněno'.\n\n"
            f"Více informací naleznete v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, recipient_emails)

    @staticmethod
    def notify_export_ready_email(user, export_record=None, download_url=None):
        """
        E-mail uživateli: asynchronní export je hotový (verb EXPORT_READY).

        ``download_url`` (nepovinná) se zahrne do textu e-mailu, pokud je dostupná.
        """
        if not user or not user.email:
            return

        subject = "Export dat je připraven"
        message = (
            "Dobrý den,\n\n"
            "Váš export dat ze systému InternHub byl dokončen a je připraven ke stažení.\n\n"
            f"Soubor stáhnete zde: {download_url}\n\n"
            if download_url
            else "Soubor stáhnete v systému InternHub.\n\n"
        )
        message += "Tým InternHub"
        EmailService._send_email(subject, message, [user.email])

    @staticmethod
    def notify_garant_contract_overdue_email(student_practice):
        """E-mail garantům: praxe je v prodlení se zasmluvněním (verb CONTRACT_OVERDUE)."""
        recipient_emails = EmailService._garant_emails(student_practice)
        if not recipient_emails:
            return
        practice = student_practice.practice
        student = student_practice.user
        practice_title = practice.title if practice else "N/A"
        student_name = student.full_name if student else "N/A"
        overdue_days = get_param("PRACTICE_CONTRACT_OVERDUE_DAYS", 7)
        subject = f"Prodlení se zasmluvněním praxe: {practice_title}"
        message = (
            f"Dobrý den,\n\n"
            f"praxe '{practice_title}' studenta {student_name} je ve stavu "
            f"'Čeká na zasmluvnění' déle než {overdue_days} dní.\n\n"
            f"Prosím o řešení v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, recipient_emails)

    # ------------------------------------------------------------------
    # notifikace garantům o registraci firem (schvalovatel = garant)
    # ------------------------------------------------------------------

    @staticmethod
    def _all_garant_emails():
        """
        E-maily všech garantů praxe napříč katedrami.

        Registrace organizace nemá vazbu na katedru/předmět, proto zde nelze
        použít resolve_garant_recipients (vyžaduje practice/subject).
        Toto je katedrově-nezávislá varianta (garanti praxe napříč katedrami).
        """
        recipients = NotificationService._all_garant_praxe()
        return [u.email for u in recipients if getattr(u, "email", "")]

    @staticmethod
    def notify_garants_new_org_registration_email(organization_user):
        """E-mail garantům: nová registrace firmy čeká na schválení (verb NEW_ORG_REGISTRATION)."""
        profile = getattr(organization_user, "employer_profile", None)
        if profile is None:
            return
        recipient_emails = EmailService._all_garant_emails()
        if not recipient_emails:
            return
        company_name = profile.company_name or organization_user.email
        ico = profile.ico or ""
        subject = f"Nová registrace organizace: {company_name}"
        message = (
            f"Dobrý den,\n\n"
            f"Do systému InternHub se zaregistrovala nová organizace:\n\n"
            f"Název: {company_name}\n"
            f"IČO: {ico}\n"
            f"Email: {organization_user.email}\n\n"
            f"Profil organizace čeká na schválení garantem.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, recipient_emails)

    @staticmethod
    def notify_garants_manual_registration_email(employer_profile):
        """E-mail garantům: firma zaregistrována s ručně zadanými údaji (verb MANUAL_REGISTRATION)."""
        recipient_emails = EmailService._all_garant_emails()
        if not recipient_emails:
            return
        company_name = employer_profile.company_name or ""
        ico = employer_profile.ico or ""
        subject = f"Registrace organizace s ručně zadanými údaji: {company_name}"
        message = (
            f"Dobrý den,\n\n"
            f"organizace {company_name} (IČO: {ico}) byla zaregistrována s ručně "
            f"zadanými údaji, které se liší od údajů v ARES, nebo ARES nebyl "
            f"dostupný.\n"
            f"Prosím zkontrolujte správnost údajů v systému InternHub.\n\n"
            f"Tým InternHub"
        )
        EmailService._send_email(subject, message, recipient_emails)


class NotificationService:
    """In-app notification service.

    Creates Notification model instances for display in the notification bell + page.
    Default ``send_email=True`` (e-mail k in-app notifikaci se odešle genericky
    přes ``NotificationService._send_email``; doménové e-maily zůstávají
    v EmailService). Pro čistě in-app notifikace se předává ``send_email=False``.
    """

    @staticmethod
    def create_notification(
        recipient,
        verb,
        message,
        actor=None,
        target=None,
        notification_type=NotificationType.INFO,
        send_email=True,
        url="",
    ):
        """
        Create an in-app notification and optionally email notification.
        Does NOT raise 500 if recipient is None.

        ``url`` je nepovinná navigační URL (FE na ni přesměruje po kliku,
        např. download URL pro EXPORT_READY).
        """
        if not recipient:
            logger.warning(f"Notification recipient is None for verb={verb}. Skipping notification.")
            return None

        try:
            notification_data = {
                "recipient": recipient,
                "actor": actor,
                "verb": verb,
                "message": message,
                "notification_type": notification_type,
            }

            if url:
                notification_data["url"] = url

            if target is not None:
                notification_data["target"] = target

            notification = Notification.objects.create(**notification_data)

            if send_email and getattr(recipient, "email", None):
                try:
                    NotificationService._send_email(recipient, verb, message)
                except Exception as mail_err:
                    logger.error(f"Failed to send email notification to {recipient.email}: {mail_err}")

            return notification
        except Exception as e:
            logger.exception(f"Failed to create notification for {recipient}: {str(e)}")
            return None

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

    # ------------------------------------------------------------------
    # Rezoluce garanta + nové notify metody
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_garant_recipients(practice_or_sp):
        """
        Vyřeší příjemce (garanty) pro notifikace o praxi.

        Závazná rezoluce:
          1. primárně ``practice.subject.subject_manager`` (pokud existuje),
          2. jinak ``ProfessorUser.objects.filter(is_garant_praxe=True,
             department=practice.subject.department)``,
          3. fallback ``ProfessorUser.objects.filter(department=practice.subject.department)``.

        Vstupem je ``Practice`` nebo ``StudentPractice`` (StudentPractice má FK ``practice``).
        Vrací list ``ProfessorUser`` instancí (může být prázdný). E-mailové adresy
        odfiltrovávají až EmailService metody.
        """
        from users.models import ProfessorUser

        practice = getattr(practice_or_sp, "practice", None) or practice_or_sp
        if practice is None:
            return []

        subject = getattr(practice, "subject", None)
        if subject is None:
            return []

        # 1) Primárně: garant = správce předmětu
        if subject.subject_manager is not None:
            return [subject.subject_manager]

        department = subject.department
        if department is None:
            return []

        # 2) Garanti praxe na katedře
        garants = list(
            ProfessorUser.objects.filter(
                is_garant_praxe=True,
                department=department,
            )
        )
        if garants:
            return garants

        # 3) Fallback: všichni profesoři katedry
        return list(ProfessorUser.objects.filter(department=department))

    @staticmethod
    def notify_garant_new_application(student_practice):
        """Nová žádost o praxi → notifikace garantů (verb NEW_APPLICATION_GARANT).

        In-app řádky vznikají transakčně (spolu s žádostí); odchozí e-mail je
        odložen na ``transaction.on_commit()`` — při rollbacku transakce
        žádná neodeslaná pošta (finding 7).
        """
        recipients = NotificationService.resolve_garant_recipients(student_practice)
        if not recipients:
            logger.warning(
                "No garant recipients resolved for NEW_APPLICATION_GARANT (sp=%s)",
                getattr(student_practice, "student_practice_id", None),
            )
            return

        practice = student_practice.practice
        student = student_practice.user
        practice_title = practice.title if practice else "N/A"
        student_name = student.full_name if student else "N/A"
        message = f"Na praxi '{practice_title}' se přihlásil nový student {student_name}.\n" f"Žádost najdete v systému InternHub."
        for recipient in recipients:
            NotificationService.create_notification(
                recipient=recipient,
                verb="NEW_APPLICATION_GARANT",
                message=message,
                actor=student_practice.user,
                target=student_practice,
                send_email=False,
            )
        transaction.on_commit(lambda: EmailService.notify_garant_new_application_email(student_practice))

    @staticmethod
    def notify_garant_cancellation(student_practice):
        """Storno praxe studentem → notifikace garantů (verb CANCELLATION_GARANT)."""
        recipients = NotificationService.resolve_garant_recipients(student_practice)
        if not recipients:
            return

        practice = student_practice.practice
        student = student_practice.user
        practice_title = practice.title if practice else "N/A"
        student_name = student.full_name if student else "N/A"
        message = f"Student {student_name} zrušil svou přihlášku na praxi '{practice_title}'.\n" f"Detaily najdete v systému InternHub."
        for recipient in recipients:
            NotificationService.create_notification(
                recipient=recipient,
                verb="CANCELLATION_GARANT",
                message=message,
                actor=student_practice.user,
                target=student_practice,
                send_email=False,
            )
        EmailService.notify_garant_cancellation_email(student_practice)

    @staticmethod
    def notify_garant_evaluation_submitted(evaluation):
        """Mentor odeslal evaluaci → notifikace garantů (verb EVALUATION_SUBMITTED)."""
        student_practice = getattr(evaluation, "student_practice", None)
        if student_practice is None:
            return
        recipients = NotificationService.resolve_garant_recipients(student_practice)
        if not recipients:
            return

        practice = student_practice.practice
        student = student_practice.user
        practice_title = practice.title if practice else "N/A"
        student_name = student.full_name if student else "N/A"
        message = f"Mentor odeslal evaluaci k praxi '{practice_title}' studenta {student_name}.\n" f"Hodnocení najdete v systému InternHub."
        for recipient in recipients:
            NotificationService.create_notification(
                recipient=recipient,
                verb="EVALUATION_SUBMITTED",
                message=message,
                actor=getattr(evaluation, "evaluated_by", None),
                target=evaluation,
                send_email=False,
            )
        EmailService.notify_garant_evaluation_submitted_email(evaluation)

    @staticmethod
    def notify_org_allocation(student_practice):
        """
        Přechod do CONTRACTED → notifikace organizace (verb ALLOCATION_ORG).

        In-app příjemce: ``practice.contact_user``. E-mail doručuje
        ``EmailService.notify_org_allocation_email`` (contact_user + owner EmployerProfile).
        """
        practice = student_practice.practice
        if practice is None:
            return

        contact_user = practice.contact_user
        if contact_user is None:
            return

        student = student_practice.user
        practice_title = practice.title or "N/A"
        student_name = student.full_name if student else "N/A"
        message = f"Praxe '{practice_title}' byla alokována studentovi {student_name} " f"a přešla do stavu 'Zasmluvněno'."
        NotificationService.create_notification(
            recipient=contact_user,
            verb="ALLOCATION_ORG",
            message=message,
            target=student_practice,
            send_email=False,
        )
        EmailService.notify_org_allocation_email(student_practice)

    @staticmethod
    def notify_export_ready(user, export_record=None, download_url=None):
        """
        Asynchronní export dokončen → notifikace žádajícího uživatele (verb EXPORT_READY).

        ``target`` je GenericFK na export záznam. Export aktuálně nemá DB model
        (cache-based, viz api/views.py DataExportView).

        ``download_url`` (nepovinná): uloží se do ``Notification.url`` (in-app,
        FE po kliku přesměruje) a zahrne se do message i do e-mailu.
        Zpětně kompatibilní s voláním ``notify_export_ready(user, None)`` (bez URL).
        """
        if user is None:
            return

        message = "Váš export dat je připraven ke stažení."
        if download_url:
            message += f"\nStáhnout: {download_url}"

        NotificationService.create_notification(
            recipient=user,
            verb="EXPORT_READY",
            message=message,
            target=export_record,
            send_email=False,
            url=download_url or "",
        )
        EmailService.notify_export_ready_email(user, export_record, download_url=download_url)

    @staticmethod
    def notify_garant_contract_overdue(student_practice):
        """Eskalace SMLOUVA_PO_TERMINU → notifikace garantů (verb CONTRACT_OVERDUE)."""
        recipients = NotificationService.resolve_garant_recipients(student_practice)
        if not recipients:
            return

        practice = student_practice.practice
        student = student_practice.user
        practice_title = practice.title if practice else "N/A"
        student_name = student.full_name if student else "N/A"
        overdue_days = get_param("PRACTICE_CONTRACT_OVERDUE_DAYS", 7)
        message = (
            f"Praxe '{practice_title}' studenta {student_name} čeká na zasmluvnění "
            f"déle než {overdue_days} dní.\n"
            f"Prosím o řešení v systému InternHub."
        )
        for recipient in recipients:
            NotificationService.create_notification(
                recipient=recipient,
                verb="CONTRACT_OVERDUE",
                message=message,
                target=student_practice,
                send_email=False,
            )
        EmailService.notify_garant_contract_overdue_email(student_practice)

    # ------------------------------------------------------------------
    # registrace firem → garanti (schvalovatel = garant)
    # ------------------------------------------------------------------

    @staticmethod
    def _all_garant_praxe():
        """
        Všichni garanti praxe (is_garant_praxe=True) napříč katedrami.

        Registrace organizace nemá vazbu na katedru/předmět, takže nelze volat
        resolve_garant_recipients (vyžaduje practice/subject). Toto je
        katedrově-nezávislá varianta větve 2 rezoluce (garanti praxe).
        """
        from users.models import ProfessorUser

        return list(ProfessorUser.objects.filter(is_garant_praxe=True).order_by("pk"))

    @staticmethod
    def notify_garants_new_org_registration(organization_user):
        """
        Nová registrace firmy → in-app + e-mail garantům.

        verb NEW_ORG_REGISTRATION. Admin notifikace zůstává doplňková
        (EmailService.notify_admins_new_org_registration).
        """
        profile = getattr(organization_user, "employer_profile", None)
        if profile is None:
            return
        company_name = profile.company_name or organization_user.email
        ico = profile.ico or ""
        message = f"Do systému se zaregistrovala nová organizace {company_name} (IČO: {ico}).\n" f"Profil čeká na schválení."
        for recipient in NotificationService._all_garant_praxe():
            NotificationService.create_notification(
                recipient=recipient,
                verb="NEW_ORG_REGISTRATION",
                message=message,
                actor=organization_user,
                target=profile,
                send_email=False,
            )
        EmailService.notify_garants_new_org_registration_email(organization_user)

    @staticmethod
    def notify_garants_manual_registration(employer_profile):
        """
        Registrace s ručně zadanými údaji → varování garantům (verb MANUAL_REGISTRATION).

        Spouští se při výpadku ARES (fallback) nebo při ručním přepisu
        údajů z ARES. In-app (WARNING) + e-mail.
        """
        company_name = employer_profile.company_name or ""
        ico = employer_profile.ico or ""
        message = (
            f"Organizace {company_name} (IČO: {ico}) byla zaregistrována s ručně " f"zadanými údaji. Prosím zkontrolujte správnost údajů."
        )
        for recipient in NotificationService._all_garant_praxe():
            NotificationService.create_notification(
                recipient=recipient,
                verb="MANUAL_REGISTRATION",
                message=message,
                target=employer_profile,
                notification_type=NotificationType.WARNING,
                send_email=False,
            )
        EmailService.notify_garants_manual_registration_email(employer_profile)
