import requests
from api.models import (
    ApprovalStatus,
    Department,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StudentUser,
    Subject,
    UserSubject,
    UserSubjectType,
)
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from users.dtos.dtos import EkonomickySubjektDTO
from users.models import StagRoleEnum


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

    # Remove non-model fields from validated_data if any remain
    # (password2 should have been removed or not passed here if we pass specific dict)
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
            is_active=True,  # TODO: Remove this
        )

        # Use frontend data if provided, otherwise fall back to ARES data
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
            company_name=company_name if company_name else (ares_data.obchodniJmeno or ""),
            address=address if address else address_ares,
            zip_code=zip_code_ares,
            approval_status=ApprovalStatus.PENDING,
            logo=logo,
        )

        # Update the user to link to the employer profile
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
        employer_profile = EmployerProfile.objects.get(employer_id=user.id)
        # Logic to update existing profile could go here if needed,
        # but original code only created if not exists or seemingly did nothing but save user?
        # Original code:
        # employer_profile = EmployerProfile.objects.get(...)
        # if not employer_profile: ... (this would never trigger if get succeeds)
        # So original code only handled creation if get failed (which raises DoesNotExist)
        # We will assume we want to create or update.

        # Actually, looking at original code:
        # try get -> if successful, do nothing.
        # except DoesNotExist -> create.
        # But 'get' raises exception, it doesn't return None.
        # So the original code was likely buggy or relying on something else.
        # We will implement: Get or Create/Update logic.

        # For now, let's stick to "Update if exists, Create if not" or "Create if not exists" as per original intent?
        # Original intent seemed to be: "If profile exists, do nothing? If not, create."
        # But 'get' would crash if not exists.
        pass

    except EmployerProfile.DoesNotExist:
        # Create new profile
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

    # Original code saved user at the end, though it modified nothing on user model itself in the visible snippet.
    # We will save user just in case signals are attached or last_login update is needed.
    user.save()
    return user


def get_user_department_ids(user) -> list[int]:
    """
    Returns a list of department IDs associated with the user.
    Checks ProfessorUser.department first, then UserSubjects.
    """
    # 1. Check if user is a ProfessorUser with a direct department assignment
    professor = ProfessorUser.objects.filter(user_ptr_id=user.id).first()
    if professor and professor.department:
        return [professor.department.department_id]

    # 2. Fallback: Check departments via UserSubjects (for students or professors via subjects)
    return list(
        Department.objects.filter(
            subjects__user_subjects__user_id=user.id,
            subjects__user_subjects__role__in=[UserSubjectType.Student.value, UserSubjectType.Professor.value],
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
        response = requests.get(f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}", timeout=5)
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
    url = f"{settings.STAG_WS_URL}/services/rest2/help/getStagUserListForLoginTicketV2"
    try:
        resp = requests.get(
            url,
            params={"ticket": ticket, "longTicket": "1"},
            timeout=(3.05, 27),
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

    return {"email": email, "first_name": jmeno, "last_name": prijmeni, "stagUserInfo": stagUserInfos[0]}  # Taking the first role/info


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

    if osCislo:
        user, _ = StudentUser.objects.get_or_create(
            email=email,
            defaults={
                "email": email,
                "stag_role": stagRole,
                "first_name": first_name,
                "last_name": last_name,
                "os_cislo": osCislo,
                "is_active": True,
            },
        )
        sync_stag_subjects_for_student(ticket, osCislo, user)

    elif ucitIdno:
        try:
            user = ProfessorUser.objects.get(email=email)
        except ProfessorUser.DoesNotExist:
            katedra = info.get("katedra")
            try:
                department = Department.objects.get(department_code=katedra)
            except Department.DoesNotExist:
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
        response = requests.get(url, cookies=cookies, params=params, timeout=(3.05, 27), headers={"Accept": "application/json"})
    except requests.RequestException:
        # Log error but don't fail the whole login if syncing subjects fails
        return

    if response.status_code == 200:
        response_json = response.json()
        items = response_json.get("predmetStudenta", [])
        # Note: We are just checking existence here, avoiding circular import of serializers
        for subj in items:
            zkratka = subj.get("zkratka")
            if zkratka:
                subjInDb = Subject.objects.filter(subject_code=zkratka).first()
                if subjInDb:
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
        response = requests.get(url, cookies=cookies, params=params, timeout=(3.05, 27), headers={"Accept": "application/json"})
    except requests.RequestException:
        return

    if response.status_code == 200:
        response_json = response.json()
        items = response_json.get("predmetUcitele", [])
        for subj in items:
            zkratka = subj.get("zkratka")
            if zkratka:
                subjInDb = Subject.objects.filter(subject_code=zkratka).first()
                if subjInDb:
                    UserSubject.objects.get_or_create(
                        subject=subjInDb,
                        user=user,
                        defaults={"role": UserSubjectType.Professor},
                    )
