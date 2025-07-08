from django.contrib.auth.forms import UserChangeForm as _UserChangeForm
from django.contrib.auth.forms import UserCreationForm as _UserCreationForm

from .models import User


class UserCreationForm(_UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "password1", "password2")


class UserChangeForm(_UserChangeForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "is_active", "is_staff")
