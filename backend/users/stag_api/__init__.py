from django.conf import settings

from .mock_client import MockStagClient
from .protocol import StagDataProvider
from .real_client import RealStagClient


def get_stag_client() -> StagDataProvider:
    """
    Factory returning either the Real or Mock STAG client based on settings.
    """
    if getattr(settings, "STAG_MOCK", False) or getattr(settings, "DEMO_LOGIN", False):
        return MockStagClient()
    return RealStagClient()
