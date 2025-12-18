from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .protocol import StagDataProvider


class MockStagClient(StagDataProvider):
    """
    Mock client providing fake data for local development/testing without VPN.
    Supports dynamic mock tickets like 'mock-student:S12345' or 'mock-teacher:U98765'.
    """

    def validate_ticket(self, ticket: str):
        # Handle generic mock student login
        if ticket == "student-ticket":
            return {
                "email": "jan.novak@ujep.cz",
                "jmeno": "Jan",
                "prijmeni": "Novák",
                "stagUserInfo": [{"role": "ST", "roleNazev": "Student", "osCislo": "S22123", "katedra": "KI", "ucitIdno": None}],
            }

        # Handle generic mock teacher login
        if ticket == "teacher-ticket":
            return {
                "email": "petr.svoboda@ujep.cz",
                "jmeno": "Petr",
                "prijmeni": "Svoboda",
                "stagUserInfo": [{"role": "VY", "roleNazev": "Vyučující", "osCislo": None, "katedra": "KI", "ucitIdno": "12345"}],
            }

        # Handle specific mock student by osCislo
        if ticket.startswith("mock-student:"):
            os_cislo = ticket.split(":")[1]
            return {
                "email": f"student_{os_cislo.lower()}@ujep.cz",
                "jmeno": "Mock",
                "prijmeni": f"Student {os_cislo}",
                "stagUserInfo": [{"role": "ST", "roleNazev": "Student", "osCislo": os_cislo, "katedra": "KI", "ucitIdno": None}],
            }

        # Handle specific mock teacher by ucitIdno
        if ticket.startswith("mock-teacher:"):
            ucit_idno = ticket.split(":")[1]
            return {
                "email": f"teacher_{ucit_idno.lower()}@ujep.cz",
                "jmeno": "Mock",
                "prijmeni": f"Teacher {ucit_idno}",
                "stagUserInfo": [{"role": "VY", "roleNazev": "Vyučující", "osCislo": None, "katedra": "KI", "ucitIdno": ucit_idno}],
            }

        # Handle existing demo-ticket
        if ticket == "demo-ticket":
            return {
                "email": "demo.student@ujep.cz",
                "jmeno": "Demo",
                "prijmeni": "Student",
                "stagUserInfo": [{"role": "ST", "roleNazev": "Student", "osCislo": "S22000", "katedra": "KI", "ucitIdno": None}],
            }

        raise AuthenticationFailed(
            "Invalid mock ticket. Use 'student-ticket', 'teacher-ticket', 'mock-student:OSCISLO', 'mock-teacher:UCITIDNO' or 'demo-ticket'."
        )

    def get_student_subjects(self, ticket: str, os_cislo: str):
        # Return generic subjects for any mock student
        if ticket.startswith("mock-student:") or ticket == "student-ticket" or ticket == "demo-ticket":
            return [
                {"zkratka": "KI/PPRO", "nazev": "Pokročilé programování", "katedra": "KI"},
                {"zkratka": "KI/DAT", "nazev": "Databázové systémy", "katedra": "KI"},
                {"zkratka": "KMA/MAT1", "nazev": "Matematika 1", "katedra": "KMA"},
            ]
        return []

    def get_teacher_subjects(self, ticket: str, ucit_idno: str):
        # Return generic subjects for any mock teacher
        if ticket.startswith("mock-teacher:") or ticket == "teacher-ticket":
            return [
                {"zkratka": "KI/PPRO", "nazev": "Pokročilé programování", "katedra": "KI"},
                {"zkratka": "KI/ZPRO", "nazev": "Základy programování", "katedra": "KI"},
            ]
        return []
