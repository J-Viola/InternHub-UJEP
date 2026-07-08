import logging

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from department.models import Department
from subject.models import Subject
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.dtos.dtos import EkonomickySubjektDTO
from users.messages import UserMessages
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StagRoleEnum,
    StudentUser,
    User,
    UserSubject,
    UserSubjectType,
)
from users.stag_api import get_stag_client

logger = logging.getLogger(__name__)


def register_organization(validated_data):
    """
    Registers a new organization user and their employer profile.
    Fetches additional data from ARES.
    """
    ico = validated_data.pop("ico")
    company_name = validated_data.pop("companyName", "")
    address = validated_data.pop("address", "")
    dic = validated_data.pop("dic", "")
    logo = validated_data.pop("logo", None)
    password = validated_data.pop("password")

    validated_data.pop("password2", None)

    ares_data = fetch_ares_data(ico)
    if not ares_data:
        raise ValueError(UserMessages.ARES_FETCH_FAILED)

    try:
        with transaction.atomic():
            user = OrganizationUser.objects.create(
                email=validated_data["email"].lower(),
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                title_before=validated_data.get("title_before", ""),
                title_after=validated_data.get("title_after", ""),
                phone=validated_data.get("phone", ""),
                organization_role=OrganizationRole.OWNER,
                is_active=True,
            )

            if hasattr(ares_data, "sidlo") and ares_data.sidlo:
                sidlo = ares_data.sidlo
                address_ares = sidlo.textovaAdresa or ""
                zip_code_ares = sidlo.psc
            else:
                address_ares = ""
                zip_code_ares = None

            employer_profile = EmployerProfile.objects.create(
                ico=ico,
                dic=dic if dic else (ares_data.dic or ""),
                company_name=(company_name if company_name else (ares_data.obchodniJmeno or "")),
                address=address if address else address_ares,
                zip_code=zip_code_ares,
                approval_status=ApprovalStatus.PENDING,
                logo=logo,
            )

            user.employer_profile = employer_profile
            user.set_password(password)
            user.save()

            ActionLogService.log(
                user=user,
                action_type=ActionLogType.REGISTER,
                object_type="OrganizationUser",
                object_id=user.id,
                description=f"Registrace organizace {employer_profile.company_name} (IČO: {ico}), email: {user.email}",
            )

            # Notify user via email only after successful transaction commit
            from notifications.services import EmailService

            transaction.on_commit(lambda: EmailService.notify_org_welcome(user))
            transaction.on_commit(lambda: EmailService.notify_admins_new_org_registration(user))

            return user
    except IntegrityError:
        raise ValueError(UserMessages.EMAIL_ALREADY_EXISTS)


def update_organization_from_ares(user, ico: str):
    """
    Updates the organization's profile with data from ARES based on the provided ICO.
    Creates an EmployerProfile if it doesn't exist.
    """
    ares_data = fetch_ares_data(ico)
    if not ares_data:
        raise ValueError(UserMessages.ARES_FETCH_FAILED)

    with transaction.atomic():
        if not (hasattr(user, "employer_profile") and user.employer_profile):
            status_enum = ApprovalStatus.PENDING

            address = ""
            zip_code = None
            if hasattr(ares_data, "sidlo") and ares_data.sidlo:
                address = ares_data.sidlo.textovaAdresa or ""
                zip_code = ares_data.sidlo.psc

            employer_profile = EmployerProfile.objects.create(
                ico=ares_data.ico,
                dic=ares_data.dic or "",
                company_name=ares_data.obchodniJmeno or "",
                address=address,
                zip_code=zip_code,
                approval_status=status_enum,
            )
            user.employer_profile = employer_profile

        user.save()

    ActionLogService.log(
        user=user,
        action_type=ActionLogType.ARES_UPDATE,
        object_type="EmployerProfile",
        object_id=user.id,
        description=f"Aktualizace organizace z ARES (IČO: {ico})",
    )

    return user


def get_user_department_ids(user) -> list[int]:
    """
    Returns a list of department IDs associated with the user.
    Checks ProfessorUser.department first, then UserSubjects.
    """
    professor = ProfessorUser.objects.filter(pk=user.id).first()
    if professor and professor.department:
        return [professor.department.department_id]

    from department.models import Department

    return list(
        Department.objects.filter(
            subjects__user_subjects__user_id=user.id,
            subjects__user_subjects__role__in=[
                UserSubjectType.Student.value,
                UserSubjectType.Professor.value,
            ],
        )
        .values_list("department_id", flat=True)
        .distinct()
    )


def fetch_ares_data(ico: str) -> EkonomickySubjektDTO | None:
    """
    Fetches company data from ARES API by ICO.
    Handles caching.
    """
    ico = str(ico).zfill(8)
    cache_key = f"ares_{ico}"
    cached_data = cache.get(cache_key)

    if cached_data:
        # Check if it's already a DTO (from internal usage) or dict (from cache)
        if isinstance(cached_data, dict):
            return EkonomickySubjektDTO.model_validate(cached_data)
        return cached_data

    try:
        url = f"{settings.ARES_API_URL}/{ico}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            response_data = response.json()
            if "kod" in response_data and response_data["kod"] is not None:
                # ARES returned a business error code inside 200 OK
                return None

            ares_dto = EkonomickySubjektDTO.model_validate(response_data)
            cache.set(cache_key, ares_dto.model_dump(), timeout=3600)
            return ares_dto
    except requests.RequestException as e:
        logger.warning("ARES lookup failed for IČO %s: %s", ico, e)
        return None

    return None


def validate_stag_ticket(ticket: str, stag_user_info: dict | None = None):
    """
    Validates STAG service ticket and returns user details.
    In mock mode, accepts pre-decoded stagUserInfo from the STAG redirect URL directly.
    In real mode, always validates the ticket against the STAG API.
    """
    if stag_user_info and not getattr(settings, "STAG_MOCK", False):
        raise AuthenticationFailed("stag_user_info is only allowed in mock/development mode")

    from users.stag_api.mock_client import MockStagClient

    client = get_stag_client()

    if stag_user_info and isinstance(client, MockStagClient):
        # Dev/mock mode: trust the stagUserInfo sent by the STAG server in the redirect URL
        details = stag_user_info
    else:
        details = client.validate_ticket(ticket)

    email = details.get("email")
    jmeno = details.get("jmeno")
    prijmeni = details.get("prijmeni")
    stagUserInfos = details.get("stagUserInfo")

    if not stagUserInfos or len(stagUserInfos) == 0:
        raise AuthenticationFailed("No user information returned by STAG")

    if not email:
        raise AuthenticationFailed("Email not returned by STAG")

    return {
        "email": email,
        "first_name": jmeno,
        "last_name": prijmeni,
        "stagUserInfo": stagUserInfos[0],
    }


def get_or_create_stag_user(stag_data: dict, ticket: str):
    """
    Creates or updates a StudentUser or ProfessorUser based on STAG data.
    Wrapped in transaction.atomic to handle concurrent STAG logins.
    """
    try:
        with transaction.atomic():
            return _get_or_create_stag_user_inner(stag_data, ticket)
    except IntegrityError:
        raise AuthenticationFailed("Concurrent STAG login conflict. Please try again.")


def _get_or_create_stag_user_inner(stag_data: dict, ticket: str):
    """
    Creates or updates a StudentUser or ProfessorUser based on STAG data.
    """
    email = stag_data["email"]
    first_name = stag_data["first_name"]
    last_name = stag_data["last_name"]
    info = stag_data["stagUserInfo"]

    role = info["role"]
    roleName = info["roleNazev"]
    osCislo = info.get("osCislo")
    ucitIdno = info.get("ucitIdno")

    try:
        stagRole, created = StagRole.objects.get_or_create(role=role, defaults={"role_name": roleName})
        if not created and stagRole.role_name != roleName:
            # If role existed, but its role_name is different from what STAG provided, update it.
            stagRole.role_name = roleName
            stagRole.save(update_fields=["role_name"])
    except IntegrityError as e:
        # If get_or_create failed, it's likely due to a unique constraint violation.
        # Since 'role' is unique and used in get_or_create, it implies that
        # the 'create' part of get_or_create failed on 'role_name' unique constraint.
        # This means another StagRole with this 'roleName' exists, but with a different 'role' code.
        # This suggests an inconsistent database state or unexpected data from STAG.
        # As a fallback, try to retrieve by role_name.
        try:
            stagRole = StagRole.objects.get(role_name=roleName)
        except StagRole.DoesNotExist:
            raise AuthenticationFailed(
                f"STAG role '{role}'/'{roleName}' lookup/creation failed due to unique constraint "
                f"violation and no fallback by role_name found. Error: {e}"
            )
        except Exception as e_inner:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Unexpected error during STAG role handling")
            raise AuthenticationFailed(f"An unexpected error occurred during STAG role handling: {e_inner}")

    user = None

    if osCislo:  # This indicates a StudentUser
        user = None
        # 1. Try finding by email
        try:
            user = StudentUser.objects.get(email__iexact=email)
        except StudentUser.DoesNotExist:
            # 2. Try finding by osCislo
            try:
                user = StudentUser.objects.get(os_cislo=osCislo)
                # Found by ID but email is different. Update email.
                user.email = email
                user.save()
            except StudentUser.DoesNotExist:
                # Not found by email nor ID -> Check for conflict with generic User
                try:
                    existing_user = User.objects.get(email__iexact=email)
                    # If we are here, user exists but is not StudentUser
                    if settings.DEMO_LOGIN:
                        if existing_user.is_staff or existing_user.is_superuser:
                            raise AuthenticationFailed(
                                f"Uživatel s emailem {email} existuje jako ADMIN/STAFF. Nelze automaticky převést na Studenta."
                            )
                        import time

                        timestamp = int(time.time())
                        existing_user.email = f"archived_{timestamp}_{existing_user.email}"
                        existing_user.is_active = False
                        existing_user.save()

                        ActionLogService.log(
                            user=None,
                            action_type=ActionLogType.UPDATE,
                            object_type="User",
                            object_id=existing_user.id,
                            description=f"Archivace uživatele {email} při STAG konfliktu (student)",
                        )
                    else:
                        raise AuthenticationFailed(
                            f"Uživatel s emailem {email} již existuje, ale není veden jako student.Kontaktujte administrátora"
                        )
                except User.DoesNotExist:
                    pass

        if user:
            if not user.is_active:
                raise AuthenticationFailed("Účet je deaktivován")
            # Update basic info
            user.first_name = first_name
            user.last_name = last_name
            user.os_cislo = osCislo
            user.stag_ticket = ticket
            user.save()
        else:
            user = StudentUser.objects.create(
                email=email.lower(),
                stag_role=stagRole,
                first_name=first_name,
                last_name=last_name,
                os_cislo=osCislo,
                stag_ticket=ticket,
                is_active=True,
            )

        # After student creation/update, try to fetch additional data from STAG
        if user.os_cislo:
            try:
                fetch_student_data_from_stag(user, ticket=ticket)
            except Exception:
                pass  # Non-critical — login should not fail if STAG data fetch fails

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.LOGIN,
            object_type="StudentUser",
            object_id=user.id,
            description=f"STAG login student: {first_name} {last_name} ({email})",
        )

        # Simple caching for sync: Only sync if created or (last_login is None or old)
        # Or simply: Always sync but with timeout handled in sync function
        sync_stag_subjects_for_student(ticket, osCislo, user)

    elif ucitIdno:
        # For professors, department assignment is critical, so we must ensure it exists
        user = None
        try:
            user = ProfessorUser.objects.get(email__iexact=email)
        except ProfessorUser.DoesNotExist:
            # Try to find by ucitIdno if email changed
            try:
                user = ProfessorUser.objects.get(ucit_idno=ucitIdno)
                # Found by ID but email is different. Update email.
                user.email = email
                user.save()
            except ProfessorUser.DoesNotExist:
                # Not found by email nor ID -> Check for conflict with generic User
                try:
                    existing_user = User.objects.get(email__iexact=email)
                    # If we are here, user exists but is not ProfessorUser
                    if settings.DEMO_LOGIN:
                        if existing_user.is_staff or existing_user.is_superuser:
                            raise AuthenticationFailed(
                                f"Uživatel s emailem {email} existuje jako ADMIN/STAFF. Nelze automaticky převést na Vyučujícího."
                            )
                        import time

                        timestamp = int(time.time())
                        existing_user.email = f"archived_{timestamp}_{existing_user.email}"
                        existing_user.is_active = False
                        existing_user.save()

                        ActionLogService.log(
                            user=None,
                            action_type=ActionLogType.UPDATE,
                            object_type="User",
                            object_id=existing_user.id,
                            description=f"Archivace uživatele {email} při STAG konfliktu (profesor)",
                        )
                    else:
                        raise AuthenticationFailed(
                            f"Uživatel s emailem {email} již existuje, ale není veden jako vyučující.Kontaktujte administrátora"
                        )
                except User.DoesNotExist:
                    pass

        if user:
            if not user.is_active:
                raise AuthenticationFailed("Účet je deaktivován")
            # Update basic info
            user.first_name = first_name
            user.last_name = last_name
            user.stag_ticket = ticket
            user.save()
        else:
            katedra = info.get("katedra")
            try:
                department = Department.objects.get(department_code=katedra)
            except Department.DoesNotExist:
                if settings.DEMO_LOGIN:
                    department, _ = Department.objects.get_or_create(department_code=settings.DEMO_DEPARTMENT_CODE)
                else:
                    raise AuthenticationFailed(f"Katedra {katedra} nebyla nalezena v databázi. Kontaktujte správce systému")

            department_role = DepartmentRole.HEAD if stagRole.role.lower() == StagRoleEnum.VK else DepartmentRole.TEACHER

            user = ProfessorUser.objects.create(
                email=email.lower(),
                stag_role=stagRole,
                first_name=first_name,
                last_name=last_name,
                ucit_idno=ucitIdno,
                stag_ticket=ticket,
                is_active=True,
                department=department,
                department_role=department_role,
            )

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.LOGIN,
            object_type="ProfessorUser",
            object_id=user.id,
            description=f"STAG login profesor: {first_name} {last_name} ({email})",
        )

        sync_stag_roles_for_teacher(ticket, ucitIdno, user)

    return user


def sync_stag_subjects_for_student(stag_ticket: str, osCislo: str, user: StudentUser):
    """
    Synchronizes STAG subjects with the database for student.
    Performs a full sync: adds new subjects and removes subjects the student is no longer enrolled in.
    SKIPPED if STAG_MOCK is True to preserve seeded development data.
    """
    if getattr(settings, "STAG_MOCK", False):
        return

    with transaction.atomic():
        client = get_stag_client()
        items = client.get_student_subjects(stag_ticket, osCislo)

        valid_subject_codes = set()

        if settings.DEMO_LOGIN:
            subject, _ = Subject.objects.get_or_create(subject_code=settings.DEMO_SUBJECT_CODE)
            UserSubject.objects.update_or_create(
                subject=subject,
                user=user,
                defaults={
                    "role": UserSubjectType.Student,
                    "is_active": True,
                },
            )
            valid_subject_codes.add(settings.DEMO_SUBJECT_CODE)

        for subj in items:
            zkratka = subj.get("zkratka")
            nazev = subj.get("nazev")
            katedra_kod = subj.get("katedra")

            department = None
            if katedra_kod:
                department, _ = Department.objects.get_or_create(department_code=katedra_kod, defaults={"department_name": katedra_kod})

            if zkratka:
                valid_subject_codes.add(zkratka)
                subjInDb, created = Subject.objects.get_or_create(
                    subject_code=zkratka,
                    defaults={"subject_name": nazev or zkratka, "department": department},
                )

                # Update department if missing or changed (optional, prioritizing STAG data)
                if department and subjInDb.department != department:
                    subjInDb.department = department
                    subjInDb.save()

                # Ensure relationship is active
                UserSubject.objects.update_or_create(
                    subject=subjInDb,
                    user=user,
                    defaults={
                        "role": UserSubjectType.Student,
                        "is_active": True,
                    },
                )

        # Soft-delete subjects the user is no longer enrolled in
        UserSubject.objects.filter(user=user, role=UserSubjectType.Student, is_active=True).exclude(
            subject__subject_code__in=valid_subject_codes
        ).update(is_active=False)

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.VIEW,
            object_type="STAG",
            object_id=user.id,
            description=f"STAG synchronizace předmětů studenta {user.email} ({len(valid_subject_codes)} předmětů)",
        )


def sync_stag_roles_for_teacher(stag_ticket: str, ucitIdno: str, user: ProfessorUser):
    """
    Synchronizes STAG roles with the database.
    Performs a full sync: adds new subjects and removes subjects the teacher no longer teaches.
    SKIPPED if STAG_MOCK is True to preserve seeded development data.
    """
    if getattr(settings, "STAG_MOCK", False):
        return

    with transaction.atomic():
        client = get_stag_client()
        items = client.get_teacher_subjects(stag_ticket, ucitIdno)

        valid_subject_codes = set()

        for subj in items:
            zkratka = subj.get("zkratka")
            nazev = subj.get("nazev")
            katedra_kod = subj.get("katedra")

            department = None
            if katedra_kod:
                department, _ = Department.objects.get_or_create(department_code=katedra_kod, defaults={"department_name": katedra_kod})

            if zkratka:
                valid_subject_codes.add(zkratka)
                subjInDb, created = Subject.objects.get_or_create(
                    subject_code=zkratka,
                    defaults={"subject_name": nazev or zkratka, "department": department},
                )

                if department and subjInDb.department != department:
                    subjInDb.department = department
                    subjInDb.save()

                UserSubject.objects.update_or_create(
                    subject=subjInDb,
                    user=user,
                    defaults={
                        "role": UserSubjectType.Professor,
                        "is_active": True,
                    },
                )

        # Soft-delete subjects the teacher is no longer assigned to
        UserSubject.objects.filter(user=user, role=UserSubjectType.Professor, is_active=True).exclude(
            subject__subject_code__in=valid_subject_codes
        ).update(is_active=False)

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.VIEW,
            object_type="STAG",
            object_id=user.id,
            description=f"STAG synchronizace předmětů učitele {user.email} ({len(valid_subject_codes)} předmětů)",
        )


def fetch_student_data_from_stag(student, ticket=None):
    """
    Fetch detailed student personal data from STAG and update the StudentUser model.

    Args:
        student: StudentUser instance (must have os_cislo and stagUser model for STAG ticket)
        ticket: Optional fresh STAG ticket. If not provided, uses the stored ticket
                from student.stag_user_ptr.stag_ticket.

    Returns:
        dict with the fetched student data, or empty dict on failure.

    Raises:
        ValueError: if student has no os_cislo
    """
    if not student.os_cislo:
        raise ValueError("Student has no os_cislo — cannot fetch from STAG")

    from django.conf import settings

    if getattr(settings, "STAG_MOCK", False) or getattr(settings, "DEMO_LOGIN", False):
        ticket = f"mock-student:{student.os_cislo}"
    else:
        if not ticket:
            ticket = student.stag_user_ptr.get_ticket()
        if not ticket:
            return {}

    client = get_stag_client()
    data = client.get_student_info(ticket, student.os_cislo)

    if not data:
        return {}

    # Update StudentUser fields from STAG data
    with transaction.atomic():
        if "datNarozeni" in data and data["datNarozeni"]:
            try:
                from datetime import datetime

                student.date_of_birth = datetime.strptime(data["datNarozeni"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        if "mistoNarozeni" in data:
            student.place_of_birth = str(data["mistoNarozeni"])[:100]
        if "ulice" in data:
            student.street = str(data["ulice"])[:100]
        if "cisloPopisne" in data:
            student.street_number = str(data["cisloPopisne"])[:10]
        if "psc" in data:
            student.zip_code = str(data["psc"])[:10]
        if "obec" in data:
            student.city = str(data["obec"])[:100]
        if "oborNazev" in data:
            student.field_of_study = str(data["oborNazev"])[:100]
        if "rocnik" in data and data["rocnik"] is not None:
            try:
                student.year_of_study = int(data["rocnik"])
            except (ValueError, TypeError):
                pass

        student.save(
            update_fields=[
                "date_of_birth",
                "place_of_birth",
                "street",
                "street_number",
                "zip_code",
                "city",
                "field_of_study",
                "year_of_study",
            ]
        )

    return data
