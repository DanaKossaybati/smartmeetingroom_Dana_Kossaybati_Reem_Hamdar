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
    
    Creates a new user account with secure password hashing and validation:
    - Validates username uniqueness (prevents duplicate usernames)
    - Validates email uniqueness (one account per email address)
    - Validates password strength via Pydantic schema constraints
    - Hashes password using bcrypt (cost factor 12) before storage
    - Creates account with is_active=True by default
    
    Args:
        user_data (schemas.UserCreate): Registration data with fields:
            - username (str, 3-50 chars): Unique login identifier
            - password (str, min 8 chars): Will be bcrypt hashed
            - email (str): Valid email, must be unique
            - full_name (str): Display name for the user
            - role (str, optional): User role (default: 'regular_user')
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        schemas.UserResponse: Created user object with fields:
            - user_id (int): Auto-generated primary key
            - username (str): The registered username
            - email (str): The registered email
            - full_name (str): Display name
            - role (str): User role
            - is_active (bool): Account active status
            - created_at (datetime): Account creation timestamp
    
    Raises:
        HTTPException(409): Username or email already registered
        HTTPException(422): Validation failed (username/password/email constraints)
    
    Example:
        POST /api/users/register
        {
            "username": "john_doe",
            "password": "SecurePass123!",
            "email": "john@example.com",
            "full_name": "John Doe",
            "role": "regular_user"
        }
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
        role=user_data.role
    )
    
    # Add to database and commit transaction
    db.add(new_user)
    db.commit()              # Persist changes to database
    db.refresh(new_user)     # Reload object to get auto-generated fields (user_id, timestamps)
    
    return new_user
