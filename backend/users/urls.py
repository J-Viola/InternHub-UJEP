from django.urls import path

from . import views
from .views import CustomTokenObtainPairView, CustomTokenRefreshView, LogoutView, RegisterView

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("ares-justice/", views.aresJustice),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("pp/", views.pp, name="pp"),
    path("authpp/", views.authpp, name="pp"),
    path('verification/', include('verify_email.urls')),
]
