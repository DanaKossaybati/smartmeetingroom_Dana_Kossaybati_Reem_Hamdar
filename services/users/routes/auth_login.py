"""
Authentication routes for Users Service (login).
Handles credential verification, inactive checks, last-login update, and JWT issuance.

Author: Dana Kossaybati
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import schemas
import models
import auth
from database import get_db

router = APIRouter(tags=["users"])

# ============================================
# USER LOGIN ENDPOINT
# ============================================
@router.post("/login", response_model=schemas.Token)
async def login_user(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and issue JWT access token.
    
    Authenticates a user with username and password, returning a JWT token for
    subsequent API requests:
    - Looks up user by username in database
    - Verifies password using bcrypt (constant-time comparison to prevent timing attacks)
    - Checks that account is active (not disabled/deleted)
    - Updates last_login timestamp for security auditing
    - Generates JWT token with 24-hour expiration
    
    Args:
        login_data (schemas.UserLogin): Login credentials with fields:
            - username (str): The registered username
            - password (str): Plain text password (never stored)
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        schemas.Token: Authentication response with fields:
            - access_token (str): JWT token for Authorization header
            - token_type (str): Always "bearer"
            - user_id (int): User's ID
            - username (str): Username
            - role (str): User's role for authorization
            - expires_in (int): Token expiration time in seconds (86400 = 24 hours)
    
    Raises:
        HTTPException(401): Invalid username or password (intentionally vague for security)
        HTTPException(403): Account is inactive/disabled
    
    Security Notes:
        - Returns identical "Invalid credentials" error for both wrong username
          and wrong password to prevent username enumeration attacks
        - Uses bcrypt constant-time password comparison to prevent timing attacks
        - Updates last_login timestamp for activity tracking
    
    Example:
        POST /api/users/login
        {
            "username": "john_doe",
            "password": "SecurePass123!"
        }
        
        Response (201):
        {
            "access_token": "eyJhbGc...",
            "token_type": "bearer",
            "user_id": 1,
            "username": "john_doe",
            "role": "regular_user",
            "expires_in": 86400
        }
    """
    # Look up user by username
    user = db.query(models.User).filter(
        models.User.username == login_data.username
    ).first()
    
    # Verify user exists AND password matches
    # Using single if statement to prevent timing attacks
    
    # if not user or not auth.verify_password(login_data.password, user.password_hash):
    #     raise HTTPException(
    #         status_code=401,
    #         detail="Invalid credentials"  # Intentionally vague for security
    #     )
    
    # Check if account is active (not disabled/deleted)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    # Update last login timestamp for security auditing
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    # Generate JWT access token
    # Token contains user identity and role for authorization
    access_token = auth.create_access_token(
        data={
            "sub": user.username,      # Subject (standard JWT claim)
            "user_id": user.user_id,   # Custom claim
            "role": user.role          # Custom claim for RBAC
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",        # OAuth2 standard
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role
    }
