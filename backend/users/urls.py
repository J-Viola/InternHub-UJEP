from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AresJusticeView, CustomTokenObtainPairView, LogoutView, RegisterView

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("ares-justice/", AresJusticeView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # path('verification/', include('verify_email.urls')),
]
