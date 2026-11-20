from datetime import date
from typing import Any

import requests
from django.conf import settings
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .exceptions import StagUnreachableError
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
            raise StagUnreachableError()

        if resp.status_code != 200:
            raise AuthenticationFailed("Autentizace ve STAGu selhala")

        return resp.json()

    def invalidate_ticket(self, ticket: str) -> None:
        url = f"{settings.STAG_WS_URL}/services/rest2/help/invalidateTicket"
        try:
            response = requests.get(url, params={"ticket": ticket}, timeout=(2, 5))
        except requests.RequestException:
            raise StagUnreachableError()
        if response.status_code != 200:
            raise StagUnreachableError()

    def _current_academic_year(self, ticket: str) -> str:
        """Aktuální akademický rok ze STAGu; při výpadku dopočet z data (rok začíná 1. 10.)."""
        url = f"{settings.STAG_WS_URL}/services/rest2/kalendar/getAktualniObdobiInfo"
        try:
            response = requests.get(
                url,
                cookies={"WSCOOKIE": ticket},
                params={"outputFormat": "JSON"},
                timeout=(2, 5),
                headers={"Accept": "application/json"},
            )
            data = response.json() if response.status_code == 200 else None
            year = data.get("akademRok") if isinstance(data, dict) else None
            if year:
                return str(year)
        except (requests.RequestException, ValueError):
            pass

        today = date.today()
        return str(today.year if today.month >= 10 else today.year - 1)

    def get_student_subjects(self, ticket: str, os_cislo: str):
        url = f"{settings.STAG_WS_URL}/services/rest2/predmety/getPredmetyByStudent"
        params = {
            "osCislo": os_cislo,
            "outputFormat": "JSON",
            "semestr": "%",
            "rok": self._current_academic_year(ticket),
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
            "rok": self._current_academic_year(ticket),
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

    def get_student_info(self, ticket: str, os_cislo: str) -> dict[str, Any]:
        url = f"{settings.STAG_WS_URL}/services/rest2/student/getStudentInfo"
        params = {"osCislo": os_cislo, "outputFormat": "JSON"}
        cookies = {"WSCOOKIE": ticket}
        try:
            response = requests.get(url, cookies=cookies, params=params, timeout=(3, 10), headers={"Accept": "application/json"})
            if response.status_code == 200:
                data = response.json()
                # STAG returns student info — extract the first result
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data
        except requests.RequestException:
            pass
        return {}
