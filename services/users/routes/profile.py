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
    Get user profile by username.
    
    Authorization rules:
    - Users can view their own profile
    - Admins can view any profile
    - Regular users cannot view other users' profiles
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
    
    Allows updating email and full_name.
    Password changes should use a separate endpoint (not implemented).
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
    
    Alternative approach: Soft delete by setting is_active=False
    This implementation performs hard delete for demonstration.
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
