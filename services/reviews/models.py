import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func

class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, index=True)
    room_id = Column(String, ForeignKey("rooms.id"))
    user_id = Column(String, ForeignKey("users.id"))
    rating = Column(Integer,nullable=False)
    comment = Column(String)
    is_flagged = Column(Boolean, default=False)
    flagged_reason = Column(String, nullable=True)
    created_at = Column(DateTime,default=datetime.now(timezone.utc))
    updated_at = Column(DateTime,default=datetime.now(timezone.utc),onupdate=datetime.now(timezone.utc))

   
    room = relationship("Room", back_populates="reviews")

    def __init__(self, room_id: str, user_id: str, rating: int, comment: str):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.room_id = room_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment
        self.is_flagged = False
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

class Room(Base):    
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, index=True)
    name = Column(String,nullable=False)
    capacity = Column(Integer,nullable=False)
    location = Column(String)
    is_available = Column(Boolean,default=True)


    bookings = relationship("Booking", back_populates="room",cascade="all, delete-orphan")
    room_equipment = relationship("RoomEquipment", back_populates="room",cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="room")

    def __init__(self,name,capacity,location,is_available=True):
        super().__init__()
        self.id=str(uuid.uuid4())
        self.name = name
        self.capacity = capacity
        self.location = location
        self.is_available = is_available
    
class Equipment(Base):    
    __tablename__ = "equipments"
    id = Column(String, primary_key=True, index=True)
    name = Column(String,nullable=False)

    room_equip=relationship("RoomEquipment", back_populates="equipment",cascade="all, delete-orphan")

    def __init__(self, name:str):
        super().__init__()
        self.id=str(uuid.uuid4())
        self.name = name

class RoomEquipment(Base):    
    __tablename__ = "room_equipments"
   
    room_id = Column(String, ForeignKey("rooms.id") ,primary_key=True)
    equipment_id = Column(String, ForeignKey("equipments.id"),primary_key=True)
    quantity = Column(Integer,default=1)


    room = relationship("Room", back_populates="room_equipment")
    equipment = relationship("Equipment", back_populates="room_equip")
    
    def __init__(self, room_id:str,equipment_id:str,quantity:int=1):
        super().__init__()
        self.room_id = room_id
        self.equipment_id = equipment_id
        self.quantity = quantity


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
    
    
