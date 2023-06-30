from enum import Enum

class UserAuthLevel(int, Enum):
    PUBLIC = 0
    PRIVATE = 1
    DEVELOPER = 2
    ADMIN = 3
    SUPERADMIN = 4