import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from department.models import Department
from subject.models import Subject
from users.dtos.dtos import EkonomickySubjektDTO
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
        raise ValueError("Failed to fetch data from ARES")

    with transaction.atomic():
        user = OrganizationUser.objects.create(
            email=validated_data["email"],
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
            employer_id=user.id,
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

        return user


def update_organization_from_ares(user, ico: str):
    """
    Updates the organization's profile with data from ARES based on the provided ICO.
    Creates an EmployerProfile if it doesn't exist.
    """
    ares_data = fetch_ares_data(ico)
    if not ares_data:
        raise ValueError("Failed to fetch data from ARES")

    try:
        EmployerProfile.objects.get(employer_id=user.id)
        # Update existing profile logic could go here if needed
    except EmployerProfile.DoesNotExist:
        status_enum = ApprovalStatus.PENDING

        address = ""
        zip_code = None
        if hasattr(ares_data, "sidlo") and ares_data.sidlo:
            address = ares_data.sidlo.textovaAdresa or ""
            zip_code = ares_data.sidlo.psc

        EmployerProfile.objects.create(
            employer_id=user.id,
            ico=ares_data.ico,
            dic=ares_data.dic or "",
            company_name=ares_data.obchodniJmeno or "",
            address=address,
            zip_code=zip_code,
            approval_status=status_enum,
        )

    user.save()
    return user


def get_user_department_ids(user) -> list[int]:
    """
    Returns a list of department IDs associated with the user.
    Checks ProfessorUser.department first, then UserSubjects.
    """
    professor = ProfessorUser.objects.filter(user_ptr_id=user.id).first()
    if professor and professor.department:
        return [professor.department.department_id]

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
    except requests.RequestException:
        return None

    return None


def validate_stag_ticket(ticket: str):
    """
    Validates STAG service ticket and returns user details.
    """
    if settings.DEMO_LOGIN and ticket == "demo-ticket":
        return {
            "email": "demo.student@ujep.cz",
            "first_name": "Demo",
            "last_name": "Student",
            "stagUserInfo": {
                "role": "ST",
                "roleNazev": "Student",
                "osCislo": "S22000",
                "katedra": "KI",
            },
        }

    url = f"{settings.STAG_WS_URL}/services/rest2/help/getStagUserListForLoginTicketV2"
    try:
        resp = requests.get(
            url,
            params={"ticket": ticket, "longTicket": "1"},
            timeout=(3.05, 27),  # Connect timeout 3s, Read timeout 27s
            headers={"Accept": "application/json"},
        )
    except requests.RequestException:
        raise AuthenticationFailed("Failed to connect to STAG")

    if resp.status_code != 200:
        raise AuthenticationFailed("Failed to authenticate with STAG")

    details = resp.json()
    email = details.get("email")
    jmeno = details.pop("jmeno")
    prijmeni = details.pop("prijmeni")
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
    """
    email = stag_data["email"]
    first_name = stag_data["first_name"]
    last_name = stag_data["last_name"]
    info = stag_data["stagUserInfo"]

    role = info["role"]
    roleName = info["roleNazev"]
    osCislo = info.get("osCislo")
    ucitIdno = info.get("ucitIdno")

    stagRole, _ = StagRole.objects.get_or_create(role=role, defaults={"role": role, "role_name": roleName})

    user = None

    if osCislo:  # This indicates a StudentUser
        user = None
        # 1. Try finding by email
        try:
            user = StudentUser.objects.get(email=email)
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
                    existing_user = User.objects.get(email=email)
                    # If we are here, user exists but is not StudentUser
                    if settings.DEMO_LOGIN:
                        existing_user.delete()
                    else:
                        raise AuthenticationFailed(
                            f"Uživatel s emailem {email} již existuje, ale není veden jako student.Kontaktujte administrátora"
                        )
                except User.DoesNotExist:
                    pass

        if user:
            # Update basic info
            user.first_name = first_name
            user.last_name = last_name
            user.os_cislo = osCislo  # Ensure os_cislo is updated
            user.save()
        else:
            user = StudentUser.objects.create(
                email=email,
                stag_role=stagRole,
                first_name=first_name,
                last_name=last_name,
                os_cislo=osCislo,
                is_active=True,
            )

        # Simple caching for sync: Only sync if created or (last_login is None or old)
        # Or simply: Always sync but with timeout handled in sync function
        sync_stag_subjects_for_student(ticket, osCislo, user)

    elif ucitIdno:
        # For professors, department assignment is critical, so we must ensure it exists
        user = None
        try:
            user = ProfessorUser.objects.get(email=email)
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
                    existing_user = User.objects.get(email=email)
                    # If we are here, user exists but is not ProfessorUser
                    if settings.DEMO_LOGIN:
                        existing_user.delete()
                    else:
                        raise AuthenticationFailed(
                            f"Uživatel s emailem {email} již existuje, ale není veden jako vyučující.Kontaktujte administrátora"
                        )
                except User.DoesNotExist:
                    pass

        if user:
            # Update basic info
            user.first_name = first_name
            user.last_name = last_name
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

            department_role = DepartmentRole.HEAD if stagRole.role == StagRoleEnum.VK else DepartmentRole.TEACHER

            user = ProfessorUser.objects.create(
                email=email,
                stag_role=stagRole,
                first_name=first_name,
                last_name=last_name,
                ucit_idno=ucitIdno,
                is_active=True,
                department=department,
                department_role=department_role,
            )

        sync_stag_roles_for_teacher(ticket, ucitIdno, user)

    return user


def sync_stag_subjects_for_student(stag_ticket: str, osCislo: str, user: StudentUser):
    """
    Synchronizes STAG roles with the database for student.
    Uses short timeout to fail fast.
    """
    url = f"{settings.STAG_WS_URL}/services/rest2/predmety/getPredmetyByStudent"
    params = {
        "osCislo": osCislo,
        "outputFormat": "JSON",
        "semestr": "%",
        "rok": "%",
    }

    cookies = {
        "WSCOOKIE": stag_ticket,
    }

    try:
        # Fail fast: 2s connect, 5s read timeout
        response = requests.get(
            url,
            cookies=cookies,
            params=params,
            timeout=(2, 5),
            headers={"Accept": "application/json"},
        )
    except requests.RequestException:
        # If sync fails, we just proceed with existing data
        return

    if response.status_code == 200:
        response_json = response.json()
        items = response_json.get("predmetStudenta", [])

        if settings.DEMO_LOGIN:
            subject, _ = Subject.objects.get_or_create(subject_code=settings.DEMO_SUBJECT_CODE)
            UserSubject.objects.get_or_create(
                subject=subject,
                user=user,
                defaults={
                    "role": UserSubjectType.Student,
                },
            )

        # We could optimize this bulk operation, but for now just ensure it runs fast
        for subj in items:
            zkratka = subj.get("zkratka")
            nazev = subj.get("nazev")
            katedra_kod = subj.get("katedra")

            department = None
            if katedra_kod:
                department, _ = Department.objects.get_or_create(department_code=katedra_kod, defaults={"department_name": katedra_kod})

            if zkratka:
                subjInDb, created = Subject.objects.get_or_create(
                    subject_code=zkratka, defaults={"subject_name": nazev or zkratka, "department": department}
                )

                # Update department if missing or changed (optional, prioritizing STAG data)
                if department and subjInDb.department != department:
                    subjInDb.department = department
                    subjInDb.save()

                UserSubject.objects.get_or_create(
                    subject=subjInDb,
                    user=user,
                    defaults={
                        "role": UserSubjectType.Student,
                    },
                )


def sync_stag_roles_for_teacher(stag_ticket: str, ucitIdno: str, user: ProfessorUser):
    """
    Synchronizes STAG roles with the database.
    Uses short timeout to fail fast.
    """
    url = f"{settings.STAG_WS_URL}/services/rest2/predmety/getPredmetyByUcitel"
    params = {
        "ucitIdno": ucitIdno,
        "outputFormat": "JSON",
        "semestr": "%",
        "rok": "%",
    }

    cookies = {
        "WSCOOKIE": stag_ticket,
    }

    try:
        response = requests.get(
            url,
            cookies=cookies,
            params=params,
            timeout=(2, 5),
            headers={"Accept": "application/json"},
        )
    except requests.RequestException:
        return

    if response.status_code == 200:
        response_json = response.json()
        items = response_json.get("predmetUcitele", [])
        for subj in items:
            zkratka = subj.get("zkratka")
            nazev = subj.get("nazev")
            katedra_kod = subj.get("katedra")

            department = None
            if katedra_kod:
                department, _ = Department.objects.get_or_create(department_code=katedra_kod, defaults={"department_name": katedra_kod})

            if zkratka:
                subjInDb, created = Subject.objects.get_or_create(
                    subject_code=zkratka, defaults={"subject_name": nazev or zkratka, "department": department}
                )

                if department and subjInDb.department != department:
                    subjInDb.department = department
                    subjInDb.save()

                UserSubject.objects.get_or_create(
                    subject=subjInDb,
                    user=user,
                    defaults={"role": UserSubjectType.Professor},
                )
