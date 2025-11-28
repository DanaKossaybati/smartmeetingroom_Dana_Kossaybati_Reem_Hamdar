"""
Profile routes for Users Service (get/update/delete by username).
Includes get, update, and delete operations with authorization (self/admin).

Author: Dana Kossaybati
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import schemas
import models
import auth
from database import get_db

router = APIRouter(tags=["users"])

# ============================================
# GET USER PROFILE ENDPOINT
# ============================================
@router.get("/{username}", response_model=schemas.UserResponse)
async def get_user_profile(
    username: str,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve user profile by username.
    
    Gets detailed user profile information. Authorization is enforced:
    users can only view their own profile unless they are administrators.
    
    Args:
        username (str): Path parameter - the username of profile to retrieve
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        schemas.UserResponse: User profile object with fields:
            - user_id (int): Unique user identifier
            - username (str): The requested user's username
            - email (str): User's email address
            - full_name (str): User's display name
            - role (str): User's role (admin, regular_user, etc.)
            - is_active (bool): Whether account is active
            - created_at (datetime): Account creation timestamp
            - updated_at (datetime): Last profile update
            - last_login (datetime): Last login timestamp
    
    Raises:
        HTTPException(403): User lacks permission to view this profile
        HTTPException(404): User with username not found
    
    Authorization Rules:
        - Users can view their own profile
        - Admins can view any user's profile
        - Regular users cannot view other users' profiles
    
    Example:
        GET /api/users/john_doe
        Authorization: Bearer <token>
        
        Response (200):
        {
            "user_id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "role": "regular_user",
            "is_active": true,
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-20T15:45:00",
            "last_login": "2024-01-28T09:15:00"
        }
    """
    # Authorization check: can only view own profile (unless admin)
    if current_user["username"] != username and current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Look up user by username
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user


# ============================================
# UPDATE USER PROFILE ENDPOINT
# ============================================
@router.put("/{username}", response_model=schemas.UserResponse)
async def update_user_profile(
    username: str,
    user_update: schemas.UserUpdate,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile information.
    
    Allows users to update their own profile (email, full_name).
    Admins can update any user's profile. Password changes are not
    supported via this endpoint (separate endpoint would be needed).
    
    Args:
        username (str): Path parameter - username of profile to update
        user_update (schemas.UserUpdate): Update data with optional fields:
            - email (str, optional): New email address
            - full_name (str, optional): New display name
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        schemas.UserResponse: Updated user profile object
    
    Raises:
        HTTPException(403): User lacks permission to update this profile
        HTTPException(404): User with username not found
        HTTPException(409): Email already in use by another user
    
    Validation Rules:
        - Email must be unique (checked against other users)
        - Email must be valid format (validated by Pydantic)
        - Cannot update username via this endpoint (separate endpoint needed)
        - Cannot update password via this endpoint
    
    Authorization Rules:
        - Users can update their own profile
        - Admins can update any user's profile
    
    Example:
        PUT /api/users/john_doe
        Authorization: Bearer <token>
        {
            "email": "newemail@example.com",
            "full_name": "John Smith"
        }
    """
    # Authorization check
    if current_user["username"] != username and current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Get user to update
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update email if provided
    if user_update.email:
        # Check if new email is already taken by another user
        existing_email = db.query(models.User).filter(
            models.User.email == user_update.email,
            models.User.user_id != user.user_id  # Exclude current user
        ).first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        user.email = user_update.email
    
    # Update full name if provided
    if user_update.full_name:
        user.full_name = user_update.full_name
    
    # Commit
    db.commit()
    db.refresh(user)
    
    return user


# ============================================
# DELETE USER ENDPOINT
# ============================================
@router.delete("/{username}")
async def delete_user_account(
    username: str,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account (hard delete).
    
    Permanently removes a user account from the system. This is a destructive
    operation that cannot be undone. Soft delete approach (setting is_active=False)
    would be safer for production systems.
    
    Args:
        username (str): Path parameter - username of account to delete
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        dict: Confirmation message with fields:
            - message (str): "User deleted successfully"
    
    Raises:
        HTTPException(403): User lacks permission to delete this account
        HTTPException(404): User with username not found
    
    Authorization Rules:
        - Users can delete their own account
        - Admins can delete any user's account
    
    Production Recommendation:
        Consider implementing soft delete instead:
        1. Set is_active=False instead of deleting
        2. Preserves foreign key relationships
        3. Allows account reactivation
        4. Maintains audit trail
    
    Example:
        DELETE /api/users/john_doe
        Authorization: Bearer <token>
        
        Response (200):
        {
            "message": "User deleted successfully"
        }
    """
    # Authorization check
    if current_user["username"] != username and current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Get user to delete
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Perform hard delete
    # For production: Consider soft delete (is_active=False) instead
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}
