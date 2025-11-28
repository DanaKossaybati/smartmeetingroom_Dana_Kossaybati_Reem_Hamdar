"""
Enumeration types for Reviews Service.
Defines role-based access control (RBAC) user roles.

Author: Reem Hamdar
"""
from enum import Enum

class UserRole(str, Enum):
    """
    User roles for role-based access control (RBAC).
    
    Defines permission levels for review management operations:
    
    Roles:
        admin: Full system access, can delete any review
        moderator: Can flag/unflag reviews for inappropriate content
        user (regular_user): Can create, update, and delete own reviews
        auditor: Read-only access for compliance and reporting
        manager (facility_manager): Can moderate reviews and view analytics
        service (service_account): For inter-service communication
    
    Usage in authorization:
        - Admin: Full access to all reviews and moderation
        - Moderator: Flag/unflag reviews, view all reviews
        - User/Manager: Create and manage own reviews
        - All authenticated users: View reviews
    """
    admin = "admin"
    moderator = "moderator"
    user = "regular_user"
    auditor = "auditor"
    manager = "facility_manager"
    service = "service_account"