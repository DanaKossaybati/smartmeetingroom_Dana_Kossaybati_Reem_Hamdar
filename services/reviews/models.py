"""
Database models for Reviews Service.
Defines SQLAlchemy ORM models for reviews, rooms, and users.

Author: Reem Hamdar
"""
from datetime import datetime, timezone

from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func

class Review(Base):
    """
    Review model representing user feedback for meeting rooms.
    
    Attributes:
        id: Primary key, auto-incrementing integer
        room_id: Foreign key to rooms table
        user_id: Foreign key to users table
        rating: Star rating 1-5 (required)
        comment: Review text content
        is_flagged: Moderation flag for inappropriate content
        flagged_reason: Explanation if review is flagged
        created_at: Timestamp when review was created
        updated_at: Timestamp of last modification
        room: Relationship to Room model
        user: Relationship to User model
    
    Business Rules:
        - Users can only review each room once
        - Rating must be between 1 and 5 stars
        - Flagged reviews may be hidden from public view
    """
    _tablename_ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer,nullable=False)
    comment = Column(String)
    is_flagged = Column(Boolean, default=False)
    flagged_reason = Column(String, nullable=True)
    created_at = Column(DateTime,default=datetime.now(timezone.utc))
    updated_at = Column(DateTime,default=datetime.now(timezone.utc),onupdate=datetime.now(timezone.utc))

   
    room = relationship("Room", back_populates="reviews")
    user = relationship("User",back_populates="user_reviews")

    def _init_(self, room_id: int, user_id: int, rating: int, comment: str):
        """
        Initialize a new Review.
        
        Args:
            room_id: ID of the room being reviewed
            user_id: ID of the user creating the review
            rating: Star rating (1-5)
            comment: Review text
        """
        super()._init_()
        self.room_id = room_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment
        self.is_flagged = False
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

class Room(Base):
    """
    Room model (simplified version for reviews service).
    
    This is a read-only reference model for room information.
    The authoritative room data lives in the rooms service.
    
    Attributes:
        id: Primary key
        name: Room name
        capacity: Maximum occupancy
        location: Physical location
        is_available: Current availability status
        reviews: Relationship to Review model
    """
    _tablename_ = "rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String,nullable=False)
    capacity = Column(Integer,nullable=False)
    location = Column(String)
    is_available = Column(Boolean,default=True)

    # Only include relationships to models that exist in this service
    reviews = relationship("Review", back_populates="room")

    def _init_(self,name,capacity,location,is_available=True):
        """
        Initialize a Room reference.
        
        Args:
            name: Room name
            capacity: Maximum capacity
            location: Physical location
            is_available: Availability status
        """
        super()._init_()
        self.name = name
        self.capacity = capacity
        self.location = location
        self.is_available = is_available


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
    _tablename_ = "users"
    
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
    user_reviews=relationship("Review",back_populates="user")
    def _repr_(self):
        """String representation for debugging."""
        return f"<User(username='{self.username}', role='{self.role}')>"