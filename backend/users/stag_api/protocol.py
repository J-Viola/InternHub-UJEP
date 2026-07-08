from typing import Any, Protocol


class StagDataProvider(Protocol):
    """
    Interface for STAG API communication.
    """

    def validate_ticket(self, ticket: str) -> dict[str, Any]:
        """
        Validates the STAG ticket and returns user info.
        Raises RequestException or AuthenticationFailed on error.
        """
        ...

    def get_student_subjects(self, ticket: str, os_cislo: str) -> list[dict[str, Any]]:
        """
        Returns list of subjects for a student.
        """
        ...

    def get_teacher_subjects(self, ticket: str, ucit_idno: str) -> list[dict[str, Any]]:
        """
        Returns list of subjects for a teacher.
        """
        ...

    def get_student_info(self, ticket: str, os_cislo: str) -> dict[str, Any]:
        """
        Returns detailed student personal information from STAG.
        Returns dict with keys: jmeno, prijmeni, email, osCislo,
        titul, datNarozeni (date_of_birth), mistoNarozeni (place_of_birth),
        ulice (street), cisloPopisne (street_number), psc (zip_code), obec (city),
        oborNazev (field_of_study), rocnik (year_of_study), formaStudia, stav.
        """
        ...
