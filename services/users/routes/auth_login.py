"""
Authentication routes for Users Service (login).
Handles credential verification, inactive checks, last-login update, and JWT issuance.

Author: Dana Kossaybati
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
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
    Authenticate user and return JWT access token.
    
    This endpoint handles user authentication:
    - Looks up user by username
    - Verifies password using bcrypt (constant-time comparison)
    - Checks if account is active
    - Updates last_login timestamp
    - Generates JWT token with user info
    
    Args:
        login_data: UserLogin schema with username and password
        db: Database session
    
    Returns:
        Token schema with access_token, user_id, username, and role
    
    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 403: If account is inactive
    
    Security Note:
        Returns same error message for invalid username/password
        to prevent username enumeration attacks.
    """
    # Look up user by username
    user = db.query(models.User).filter(
        models.User.username == login_data.username
    ).first()
    
    # Verify user exists AND password matches
    # Using single if statement to prevent timing attacks
    if not user or not auth.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"  # Intentionally vague for security
        )
    
    # Check if account is active (not disabled/deleted)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    # Update last login timestamp for security auditing
    user.last_login = datetime.utcnow()
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
