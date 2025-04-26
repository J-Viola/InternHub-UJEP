from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("login/", views.login),
    path("auth-callback/", views.auth_callback),
    path("ares-justice/", views.aresJustice),
]
