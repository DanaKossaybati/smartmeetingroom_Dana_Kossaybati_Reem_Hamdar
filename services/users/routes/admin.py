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
    
    This endpoint is protected by admin authorization.
    Only users with role='admin' can access this.
    """
    # Get all users from database
    # No filtering - admins see everything
    users = db.query(models.User).all()
    return users
