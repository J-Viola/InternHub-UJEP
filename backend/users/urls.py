from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminOrganizationViewSet,
    AresJusticeView,
    CurrentUserProfileView,
    CustomTokenObtainPairView,
    LogoutView,
    OrganizationUserListView,
    RegisterView,
    StudentProfileView,
)

app_name = "users"

router = routers.DefaultRouter()
router.register(r"admin-organization-users", AdminOrganizationViewSet, basename="admin_organization_users")

urlpatterns = [
    path("", include(router.urls)),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("ares-justice/", AresJusticeView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("organization-users/", OrganizationUserListView.as_view(), name="organization_users"),
    path("student-profile/<int:student_id>", StudentProfileView.as_view(), name="student_profile"),
    path("profile/", CurrentUserProfileView.as_view(), name="current_user_profile"),
    # path('verification/', include('verify_email.urls')),
]
