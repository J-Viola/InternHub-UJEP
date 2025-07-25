from enum import Enum

# Create your models here.


class UserType(Enum):
    ADMIN = "admin"
    STAG = "stag"
    ORGANIZATION = "organization"

    def values(self):
        return [member.value for member in self.__class__]


class StagRoleEnum(Enum):
    ST = "st"
    VY = "vy"
    VK = "vk"
