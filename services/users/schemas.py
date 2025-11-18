"""
Pydantic schemas for request/response validation.
These schemas validate incoming data and structure API responses.

Author: Team Member 1
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    """
    Schema for user registration requests.
    Validates all required fields before account creation.
    """
    username: str = Field(
        ...,                  # Required field
        min_length=3,         # Minimum 3 characters
        max_length=50,        # Maximum 50 characters
        description="Unique username for login"
    )
    password: str = Field(
        ...,
        min_length=8,         # Enforce minimum password length
        description="Password (min 8 chars, requires uppercase, lowercase, number)"
    )
    email: EmailStr = Field(  # EmailStr auto-validates email format
        ...,
        description="Valid email address"
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's full name"
    )
    role: Optional[str] = Field(
        default="regular_user",
        description="User role (admin, regular_user, facility_manager, etc.)"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """
        Additional password validation beyond length.
        Requires uppercase, lowercase, and number.
        """
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v

class UserLogin(BaseModel):
    """Schema for login requests."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class UserResponse(BaseModel):
    """
    Schema for user data responses.
    Excludes sensitive information like password_hash.
    """
    user_id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]
    
    class Config:
        # Allow ORM model to be converted to Pydantic model
        from_attributes = True

class UserUpdate(BaseModel):
    """Schema for profile update requests. All fields optional."""
    email: Optional[EmailStr] = Field(None, description="New email address")
    full_name: Optional[str] = Field(None, min_length=1, max_length=100, description="New full name")

class Token(BaseModel):
    """Schema for JWT token responses."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type (always 'bearer')")
    user_id: int = Field(..., description="Authenticated user ID")
    username: str = Field(..., description="Authenticated username")
    role: str = Field(..., description="User role for authorization")
