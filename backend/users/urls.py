from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminOrganizationViewSet,
    AllStudentsListView,
    AresJusticeView,
    CurrentUserProfileView,
    CustomTokenObtainPairView,
    LogoutView,
    RegisterView,
    UpdateAresSubjectView,
)

app_name = "users"

router = routers.DefaultRouter()
router.register(
    r"organization-users",
    AdminOrganizationViewSet,
    basename="organization_users",
)

urlpatterns = [
    path("", include(router.urls)),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("ares-justice/", AresJusticeView.as_view()),
    path("ares/update/", UpdateAresSubjectView.as_view(), name="update-ares"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", CurrentUserProfileView.as_view(), name="current_user_profile"),
    path("all-students/", AllStudentsListView.as_view(), name="all_students"),
    # path('verification/', include('verify_email.urls')),
]
