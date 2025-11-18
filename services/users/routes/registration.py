"""
Registration routes for Users Service.
Implements user account creation with validation and secure password hashing.

Author: Dana Kossaybati
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import schemas
import models
import auth
from database import get_db

# Note: we set tags=["users"] to preserve grouping in docs.
# We DO NOT set a prefix here; the master router will add "/api/users".
router = APIRouter(tags=["users"])

# ============================================
# USER REGISTRATION ENDPOINT
# ============================================
@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    This endpoint handles user registration with validation and security:
    - Validates username uniqueness (prevents duplicates)
    - Validates email uniqueness (one account per email)
    - Validates password strength (handled by Pydantic schema)
    - Hashes password using bcrypt before storage
    - Creates inactive account by default (can be changed)
    
    Args:
        user_data: UserCreate schema with username, password, email, full_name, role
        db: Database session (injected by FastAPI dependency)
    
    Returns:
        UserResponse schema with created user details (excludes password)
    
    Raises:
        HTTPException 409: If username or email already exists
        HTTPException 422: If validation fails (automatic from Pydantic)
    """
    # Check if username or email already exists
    # Using OR condition to check both in single query for efficiency
    existing_user = db.query(models.User).filter(
        (models.User.username == user_data.username) | (models.User.email == user_data.email)
    ).first()
    
    if existing_user:
        # Provide specific error message for better UX
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
    
    # Create new user with hashed password
    # NEVER store plain text passwords!
    new_user = models.User(
        username=user_data.username,
        password_hash=auth.hash_password(user_data.password),  # Bcrypt hashing
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        created_at=datetime.utcnow()
    )
    
    # Add to database and commit transaction
    db.add(new_user)
    db.commit()              # Persist changes to database
    db.refresh(new_user)     # Reload object to get auto-generated fields (user_id, timestamps)
    
    return new_user
