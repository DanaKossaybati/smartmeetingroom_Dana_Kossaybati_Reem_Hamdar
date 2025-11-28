"""
Database models for Rooms Service.
Defines SQLAlchemy ORM models for rooms, equipment, and their relationships.

Author: Reem Hamdar
"""
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import ForeignKey, Column, Boolean, Integer, String, Date, Time, DateTime, Text
from sqlalchemy.sql import func


class Room(Base):
    """
    Room model representing meeting rooms.
    
    Attributes:
        id: Primary key, auto-incrementing integer
        name: Room name (required)
        capacity: Maximum number of people (required)
        location: Physical location of the room
        is_available: Current availability status (default: True)
        room_equipment: Relationship to equipment in this room
    
    Relationships:
        - One-to-many with RoomEquipment (cascade delete)
    """
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String,nullable=False)
    capacity = Column(Integer,nullable=False)
    location = Column(String)
    is_available = Column(Boolean,default=True)


    # Relationships to models in this service only
    room_equipment = relationship("RoomEquipment", back_populates="room",cascade="all, delete-orphan")

    def __init__(self,name,capacity,location,is_available=True):
        """
        Initialize a new Room.
        
        Args:
            name: Room name
            capacity: Maximum capacity
            location: Physical location
            is_available: Initial availability status (default: True)
        """
        super().__init__()
        self.name = name
        self.capacity = capacity
        self.location = location
        self.is_available = is_available
    
class Equipment(Base):
    """
    Equipment model representing room amenities and resources.
    
    Attributes:
        id: Primary key, auto-incrementing integer
        name: Equipment name (required)
        room_equip: Relationship to rooms that have this equipment
    
    Relationships:
        - One-to-many with RoomEquipment (cascade delete)
    
    Examples:
        - Projector
        - Whiteboard
        - Conference Phone
        - Video Camera
    """
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String,nullable=False)

    room_equip=relationship("RoomEquipment", back_populates="equipment",cascade="all, delete-orphan")

    def __init__(self, name:str):
        """
        Initialize new Equipment.
        
        Args:
            name: Equipment name
        """
        super().__init__()
        self.name = name

class RoomEquipment(Base):
    """
    Association table linking rooms and equipment with quantities.
    
    This is a many-to-many relationship table that tracks:
    - Which equipment is in which room
    - How many units of each equipment
    
    Attributes:
        room_id: Foreign key to rooms table (composite primary key)
        equipment_id: Foreign key to equipments table (composite primary key)
        quantity: Number of units (default: 1)
        room: Relationship back to Room
        equipment: Relationship back to Equipment
    
    Example:
        Room "Board Room" has:
        - 2x Projectors (quantity=2)
        - 1x Whiteboard (quantity=1)
    """
    __tablename__ = "room_equipment"
   
    room_id = Column(Integer, ForeignKey("rooms.id") ,primary_key=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"),primary_key=True)
    quantity = Column(Integer,default=1)


    room = relationship("Room", back_populates="room_equipment")
    equipment = relationship("Equipment", back_populates="room_equip")
    
    def __init__(self, room_id:int,equipment_id:int,quantity:int=1):
        """
        Initialize room-equipment association.
        
        Args:
            room_id: ID of the room
            equipment_id: ID of the equipment
            quantity: Number of units (default: 1)
        """
        super().__init__()
        self.room_id = room_id
        self.equipment_id = equipment_id
        self.quantity = quantity


# User and Booking models removed - they belong to users_service and bookings_service respectively
# In microservices architecture, each service owns its domain models