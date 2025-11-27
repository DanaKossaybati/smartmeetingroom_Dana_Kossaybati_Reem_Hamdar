from enum import Enum

class UserRole(str, Enum):
    admin = "admin"
    moderator = "moderator"
    user = "regular_user"
    auditor = "auditor"
    manager = "facility_manager"
    service = "service_account"