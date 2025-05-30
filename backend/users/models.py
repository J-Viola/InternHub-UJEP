from enum import Enum

# Create your models here.


class UserType(Enum):
    ADMIN = "admin"
    STUDENT = ("student",)
    ORGANIZATION = "organization"
