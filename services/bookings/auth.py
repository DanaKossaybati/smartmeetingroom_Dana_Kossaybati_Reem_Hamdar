"""
Authentication utilities for Bookings Service.
Validates JWT tokens and enforces authorization rules.

Author: Dana Kossaybati
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# OAuth2 scheme for token authentication
# Tells FastAPI where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency function to extract and validate current user from JWT token.
    
    Validates the token signature and expiration.
    Extracts user claims (user_id, username, role) for authorization.
    
    Args:
        token: JWT token from Authorization header (Bearer token)
    
    Returns:
        Dictionary with user_id, username, and role
    
    Raises:
        HTTPException 401: If token is invalid, expired, or missing
    
    Usage in routes:
        @router.get("/bookings")
        async def get_bookings(current_user: dict = Depends(get_current_user)):
            # current_user contains validated user info
            pass
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode and verify JWT signature and expiration
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract username from 'sub' claim (JWT standard)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # Return user information for use in route handlers
        return {
            "username": username,
            "user_id": payload.get("user_id"),
            "role": payload.get("role")
        }
    except JWTError:
        # Token is invalid, expired, or tampered with
        raise credentials_exception

def require_admin_or_manager(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to require admin or facility_manager role.
    
    Used for endpoints that need elevated permissions.
    
    Args:
        current_user: User dict from get_current_user dependency
    
    Returns:
        Same user dict if authorized
    
    Raises:
        HTTPException 403: If user lacks required role
    
    Usage:
        @router.delete("/bookings/{id}")
        async def force_cancel(current_user: dict = Depends(require_admin_or_manager)):
            # Only admins/managers reach here
            pass
    """
    if current_user["role"] not in ["admin", "facility_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Facility Manager access required"
        )
    return current_user
