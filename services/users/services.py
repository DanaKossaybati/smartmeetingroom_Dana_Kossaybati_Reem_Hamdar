"""
Business logic layer for Users Service.
Handles all user-related operations independently of HTTP layer.

This follows the Service Layer pattern:
- Routes handle HTTP (request/response)
- Services handle business logic
- Models handle data persistence

Author: Dana Kossaybati
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import Optional, List

import models
import schemas
import auth
from utils import sanitize_input, validate_password_strength, validate_username
from errors import UserNotFoundException, DuplicateUserException, UnauthorizedException

class UserService:
    """
    Service class containing all user-related business logic.
    Keeps routes thin and business logic testable.
    """
    
    @staticmethod
    def create_user(db: Session, user_data: schemas.UserCreate) -> models.User:
        """
        Create a new user account.
        
        Business logic:
        1. Validate username format
        2. Validate password strength
        3. Sanitize all inputs
        4. Check for duplicates
        5. Hash password
        6. Create user record
        
        Args:
            db: Database session
            user_data: User creation data from request
        
        Returns:
            Created User model instance
        
        Raises:
            DuplicateUserException: If username or email exists
            ValueError: If validation fails
        """
        # Validate username format
        is_valid, error_msg = validate_username(user_data.username)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Sanitize all string inputs (defense in depth)
        username = sanitize_input(user_data.username)
        email = sanitize_input(user_data.email)
        full_name = sanitize_input(user_data.full_name)
        role = sanitize_input(user_data.role)
        
        # Check for existing username
        existing_user = db.query(models.User).filter(
            models.User.username == username
        ).first()
        if existing_user:
            raise DuplicateUserException("username", username)
        
        # Check for existing email
        existing_email = db.query(models.User).filter(
            models.User.email == email
        ).first()
        if existing_email:
            raise DuplicateUserException("email", email)
        
        # Hash the password (never store plain text!)
        hashed_password = auth.hash_password(user_data.password)
        
        # Create new user instance
        new_user = models.User(
            username=username,
            password_hash=hashed_password,
            email=email,
            full_name=full_name,
            role=role
        )
        
        # Persist to database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)  # Refresh to get auto-generated fields
        
        return new_user
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
        """
        Authenticate user credentials.
        
        Business logic:
        1. Find user by username
        2. Verify password hash
        3. Check if account is active
        4. Update last login timestamp
        
        Args:
            db: Database session
            username: Username to authenticate
            password: Plain text password to verify
        
        Returns:
            User model if authentication successful, None otherwise
        
        Security notes:
        - Uses constant-time comparison for password
        - Doesn't reveal whether username or password was wrong (prevents enumeration)
        """
        # Find user by username
        user = db.query(models.User).filter(
            models.User.username == username
        ).first()
        
        # User not found
        if not user:
            return None
        
        # Verify password using bcrypt (constant-time comparison)
        if not auth.verify_password(password, user.password_hash):
            return None
        
        # Check if account is active
        if not user.is_active:
            return None
        
        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        return user
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> models.User:
        """
        Retrieve user by username.
        
        Args:
            db: Database session
            username: Username to find
        
        Returns:
            User model instance
        
        Raises:
            UserNotFoundException: If user doesn't exist
        """
        username = sanitize_input(username)
        
        user = db.query(models.User).filter(
            models.User.username == username
        ).first()
        
        if not user:
            raise UserNotFoundException(username)
        
        return user
    
    @staticmethod
    def get_all_users(db: Session) -> List[models.User]:
        """
        Retrieve all users (admin only).
        
        Args:
            db: Database session
        
        Returns:
            List of all User models
        """
        return db.query(models.User).all()
    
    @staticmethod
    def update_user(
        db: Session,
        username: str,
        update_data: schemas.UserUpdate
    ) -> models.User:
        """
        Update user profile information.
        
        Business logic:
        1. Find user
        2. Validate new email isn't taken
        3. Sanitize inputs
        4. Update fields
        5. Update timestamp
        
        Args:
            db: Database session
            username: Username of user to update
            update_data: Fields to update
        
        Returns:
            Updated User model
        
        Raises:
            UserNotFoundException: If user doesn't exist
            DuplicateUserException: If new email is taken
        """
        # Get existing user
        user = UserService.get_user_by_username(db, username)
        
        # Update email if provided
        if update_data.email:
            # Check if email is already taken by another user
            existing = db.query(models.User).filter(
                models.User.email == update_data.email,
                models.User.user_id != user.user_id  # Exclude current user
            ).first()
            
            if existing:
                raise DuplicateUserException("email", update_data.email)
            
            user.email = sanitize_input(update_data.email)
        
        # Update full name if provided
        if update_data.full_name:
            user.full_name = sanitize_input(update_data.full_name)
        
        
        # Commit changes
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def delete_user(db: Session, username: str) -> None:
        """
        Delete user account.
        
        Args:
            db: Database session
            username: Username to delete
        
        Raises:
            UserNotFoundException: If user doesn't exist
        """
        user = UserService.get_user_by_username(db, username)
        
        # Delete user (cascade will handle related records)
        db.delete(user)
        db.commit()
    
    @staticmethod
    def check_authorization(current_user: dict, target_username: str) -> None:
        """
        Check if current user is authorized to access target user's data.
        
        Authorization rules:
        - Users can access their own data
        - Admins can access any user's data
        
        Args:
            current_user: Dict with current user info from JWT
            target_username: Username being accessed
        
        Raises:
            UnauthorizedException: If access denied
        """
        # Allow if user is accessing their own data
        if current_user["username"] == target_username:
            return
        
        # Allow if user is admin
        if current_user["role"] == "admin":
            return
        
        # Otherwise, deny access
        raise UnauthorizedException(
            f"You don't have permission to access user '{target_username}'"
        )
