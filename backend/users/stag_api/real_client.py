import requests
from django.conf import settings
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .protocol import StagDataProvider


class RealStagClient(StagDataProvider):
    def validate_ticket(self, ticket: str):
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

        return resp.json()

    def get_student_subjects(self, ticket: str, os_cislo: str):
        url = f"{settings.STAG_WS_URL}/services/rest2/predmety/getPredmetyByStudent"
        params = {
            "osCislo": os_cislo,
            "outputFormat": "JSON",
            "semestr": "%",
            "rok": "%",
        }
        cookies = {"WSCOOKIE": ticket}

        try:
            response = requests.get(
                url,
                cookies=cookies,
                params=params,
                timeout=(2, 5),
                headers={"Accept": "application/json"},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("predmetStudenta", [])
        except requests.RequestException:
            pass

        return []

    def get_teacher_subjects(self, ticket: str, ucit_idno: str):
        url = f"{settings.STAG_WS_URL}/services/rest2/predmety/getPredmetyByUcitel"
        params = {
            "ucitIdno": ucit_idno,
            "outputFormat": "JSON",
            "semestr": "%",
            "rok": "%",
        }
        cookies = {"WSCOOKIE": ticket}

        try:
            response = requests.get(
                url,
                cookies=cookies,
                params=params,
                timeout=(2, 5),
                headers={"Accept": "application/json"},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("predmetUcitele", [])
        except requests.RequestException:
            pass

        return []
