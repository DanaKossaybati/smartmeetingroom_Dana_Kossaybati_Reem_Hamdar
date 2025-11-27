"""
Authentication and authorization utilities.
Handles password hashing, JWT token creation/validation, and access control.

Author: "Reem Hamdar"
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

pwd_context = CryptContext(
    schemes=["bcrypt"],     
    deprecated="auto"       
)

# OAuth2 scheme for token authentication
# Tells FastAPI where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")

def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Bcrypt automatically:
    - Generates a random salt
    - Uses cost factor 12 (2^12 iterations)
    - Produces a 60-character hash
    
    Args:
        password: Plain text password from user
    
    Returns:
        Hashed password string safe for database storage
    
    Example:
        hash_password("MyPassword123") -> "$2b$12$..."
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a stored hash.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        plain_password: Password provided during login
        hashed_password: Stored hash from database
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    JWT structure:
    - Header: Algorithm and token type
    - Payload: User data (sub, user_id, role, exp)
    - Signature: Cryptographic signature using SECRET_KEY
    
    Args:
        data: Dictionary containing user information to encode
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    
    Example token payload:
        {
            "sub": "username",
            "user_id": 123,
            "role": "admin",
            "exp": 1234567890
        }
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add expiration to payload
    to_encode.update({"exp": expire})
    
    # Create signed JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency function to get the currently authenticated user from JWT token.
    
    Validates the token and extracts user information.
    Raises HTTPException if token is invalid or expired.
    
    Args:
        token: JWT token from Authorization header (Bearer token)
    
    Returns:
        Dictionary with user_id, username, and role
    
    Raises:
        HTTPException 401: If token is invalid or expired
    
    Usage in routes:
        @app.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            return {"user": current_user["username"]}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},  # Tell client to send Bearer token
    )
    
    try:
        # Decode and verify JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract username from 'sub' claim (standard JWT practice)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # Return user information for use in routes
        return {
            "username": username,
            "user_id": payload.get("user_id"),
            "role": payload.get("role")
        }
    except JWTError:
        # Token is invalid, expired, or tampered with
        raise credentials_exception

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency function to require admin role.
    
    Use this to protect admin-only endpoints.
    
    Args:
        current_user: User dict from get_current_user dependency
    
    Returns:
        Same user dict if admin, raises exception otherwise
    
    Raises:
        HTTPException 403: If user is not an admin
    
    Usage:
        @app.delete("/users/{id}")
        async def delete_user(current_user: dict = Depends(require_admin)):
            # Only admins can reach this code
            pass
    """
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
