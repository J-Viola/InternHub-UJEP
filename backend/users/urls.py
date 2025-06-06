from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .views import CustomTokenObtainPairView, LogoutView, RegisterView

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("ares-justice/", views.aresJustice),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("pp/", views.pp, name="pp"),
    path("authpp/", views.authpp, name="pp"),
]
