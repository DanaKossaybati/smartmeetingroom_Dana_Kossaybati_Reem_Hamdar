"""
SQLAlchemy database models for Users Service.
Defines the User table structure and ORM mappings.

Author: Team Member 1
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    """
    User model representing system users.
    
    Handles user authentication, profile information, and role-based access control.
    Passwords are stored as bcrypt hashes (never plain text).
    
    Attributes:
        user_id: Primary key, auto-incremented
        username: Unique identifier for login (indexed for fast lookups)
        password_hash: Bcrypt hashed password (cost factor 12)
        email: Unique email address (indexed for recovery/notifications)
        full_name: Display name for the user
        role: RBAC role (admin, regular_user, facility_manager, moderator, auditor)
        is_active: Soft delete flag (false = account disabled)
        created_at: Account creation timestamp (auto-set)
        updated_at: Last profile modification (auto-updated on changes)
        last_login: Tracks user activity for security auditing
    """
    __tablename__ = "users"
    
    # Primary key - auto-incremented integer
    user_id = Column(Integer, primary_key=True, index=True)
    
    # Authentication fields
    username = Column(
        String(50), 
        unique=True,      # No duplicate usernames allowed
        nullable=False,   # Required field
        index=True        # Indexed for fast login queries
    )
    password_hash = Column(
        String(255),      # Long enough for bcrypt hash
        nullable=False    # Password is mandatory
    )
    
    # Contact information
    email = Column(
        String(100),
        unique=True,      # No duplicate emails
        nullable=False,
        index=True        # Fast email lookups for recovery
    )
    
    # Profile information
    full_name = Column(
        String(100),
        nullable=False
    )
    
    # Access control
    role = Column(
        String(20),
        nullable=False,
        default="regular_user"  # Default role for new users
    )
    
    # Account status
    is_active = Column(
        Boolean,
        default=True      # New accounts are active by default
    )
    
    # Timestamps for auditing
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()  # PostgreSQL sets this automatically
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()        # Auto-update on any change
    )
    last_login = Column(
        DateTime(timezone=True),
        nullable=True              # Null until first login
    )
    
    def __repr__(self):
        """String representation for debugging."""
        return f"<User(username='{self.username}', role='{self.role}')>"
