"""
Admin-only routes for Users Service.
Provides admin-only endpoints (e.g., list all users).

Author: Dana Kossaybati
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import schemas
import models
import auth
from database import get_db

router = APIRouter(tags=["users"])

# ============================================
# GET ALL USERS ENDPOINT (ADMIN ONLY)
# ============================================
@router.get("/", response_model=list[schemas.UserResponse])
async def get_all_users(
    current_user: dict = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users in the system (Admin only).
    
    Retrieves a list of all registered users in the system. This endpoint
    is protected and only accessible to users with admin role.
    
    Args:
        current_user (dict): Current authenticated admin user from JWT token (FastAPI dependency)
            Must have role='admin' or raises 403 Forbidden
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        list[schemas.UserResponse]: List of all user profile objects with fields:
            - user_id (int): Unique user identifier
            - username (str): Login username
            - email (str): User's email address
            - full_name (str): User's display name
            - role (str): User's role
            - is_active (bool): Whether account is active
            - created_at (datetime): Account creation timestamp
            - updated_at (datetime): Last profile modification
            - last_login (datetime): Most recent login
    
    Raises:
        HTTPException(403): User is not an admin
        HTTPException(401): User not authenticated
    
    Authorization:
        Only users with role='admin' can access this endpoint.
        Enforced by auth.require_admin dependency.
    
    Example:
        GET /api/users/
        Authorization: Bearer <admin_token>
        
        Response (200):
        [
            {
                "user_id": 1,
                "username": "admin_user",
                "email": "admin@example.com",
                "full_name": "Administrator",
                "role": "admin",
                "is_active": true,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-28T09:15:00",
                "last_login": "2024-01-28T09:15:00"
            },
            {
                "user_id": 2,
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "John Doe",
                "role": "regular_user",
                "is_active": true,
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-20T15:45:00",
                "last_login": "2024-01-28T08:00:00"
            }
        ]
    """
    # Get all users from database
    # No filtering - admins see everything
    users = db.query(models.User).all()
    return users
