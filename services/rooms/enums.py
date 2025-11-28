"""
Enumeration types for Rooms Service.
Defines role-based access control (RBAC) user roles.

Author: Reem Hamdar
"""
from enum import Enum

class UserRole(str, Enum):
    """
    User roles for role-based access control (RBAC).
    
    Defines permission levels for room management operations:
    
    Roles:
        admin: Full system access, can perform all operations
        moderator: Can moderate content and manage reviews
        user (regular_user): Standard user, can view rooms and create bookings
        auditor: Read-only access for compliance and reporting
        manager (facility_manager): Can manage rooms and equipment
        service (service_account): For inter-service communication
    
    Usage in authorization:
        - Admin/Manager: Create, update, delete rooms
        - All authenticated users: View rooms, check availability
        - Service accounts: Internal API calls between microservices
    """
    admin = "admin"
    moderator = "moderator"
    user = "regular_user"
    auditor = "auditor"
    manager = "facility_manager"
    service = "service_account"