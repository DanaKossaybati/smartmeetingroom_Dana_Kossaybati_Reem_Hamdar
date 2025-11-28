"""
Database models for Rooms Service.
Defines SQLAlchemy ORM models for rooms, equipment, and their relationships.

Author: Reem Hamdar
"""
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import ForeignKey, Column, Boolean, Integer, String, Date, Time, DateTime, Text
from sqlalchemy.sql import func


class RoomEquipment(Base):
    """
    Association table linking rooms to equipment with quantities.
    
    This model represents the many-to-many relationship between rooms
    and equipment, allowing each room to have multiple equipment items
    and each equipment type to be in multiple rooms.
    
    Attributes:
        room_id: Foreign key to rooms table (composite primary key)
        equipment_id: Foreign key to equipment table (composite primary key)
        quantity: Number of equipment units in the room (default: 1)
        room: Relationship to Room model
        equipment: Relationship to Equipment model
    
    Note:
        Uses composite primary key (room_id, equipment_id) to ensure
        each equipment type can only be assigned once per room.
    """
    __tablename__ = "room_equipment"

    room_id = Column(Integer, ForeignKey("rooms.room_id"), primary_key=True)
    equipment_id = Column(Integer, ForeignKey("equipment.equipment_id"), primary_key=True)
    quantity = Column(Integer, default=1)

    room = relationship("Room", back_populates="room_equipment")
    equipment = relationship("Equipment", back_populates="room_equipment")

    def __init__(self, room_id:int,equipment_id:int,quantity:int=1):
        """
        Initialize a room-equipment association.
        
        Args:
            room_id: ID of the room
            equipment_id: ID of the equipment
            quantity: Number of equipment units (default: 1)
        """
        super().__init__()
        self.room_id = room_id
        self.equipment_id = equipment_id
        self.quantity = quantity

class Room(Base):
    """
    Room model representing meeting rooms in the system.
    
    Maps to the 'rooms' table in the database with column name mappings
    to match the existing database schema.
    
    Attributes:
        id: Primary key (mapped to room_id column)
        name: Room name (mapped to room_name column)
        capacity: Maximum occupancy
        location: Physical location of the room
        is_available: Availability status (mapped to status column)
        room_equipment: Relationship to RoomEquipment association table
    
    Business Rules:
        - Room names should be unique
        - Capacity must be positive
        - Status must be: 'available', 'unavailable', or 'maintenance'
        - Deleting a room cascades to remove all equipment associations
    """    
    __tablename__ = "rooms"

    id = Column("room_id", Integer, primary_key=True, index=True, autoincrement=True)
    name = Column("room_name", String, nullable=False)
    capacity = Column(Integer, nullable=False)
    location = Column(String)
    is_available = Column("status",String, default='available')

    # Relationships to models in this service only
    room_equipment = relationship("RoomEquipment", back_populates="room", cascade="all, delete-orphan")

    def __init__(self,name,capacity,location,is_available='available'):
        """
        Initialize a new Room.
        
        Args:
            name: Room name/identifier
            capacity: Maximum number of people
            location: Physical location description
            is_available: Initial availability status (default: 'available')
                         Can be 'available', 'unavailable', or 'maintenance'
        
        Note:
            Handles both boolean and string values for backward compatibility.
            Boolean True maps to 'available', False maps to 'unavailable'.
        """
        super().__init__()
        self.name = name
        self.capacity = capacity
        self.location = location
        # Handle both boolean and string values for status
        if isinstance(is_available, bool):
            self.is_available = 'available' if is_available else 'unavailable'
        else:
            self.is_available = is_available
    
class Equipment(Base):
    """
    Equipment model representing available meeting room equipment.
    
    Maps to the 'equipment' table with column name mappings to match
    the existing database schema.
    
    Attributes:
        id: Primary key (mapped to equipment_id column)
        name: Equipment name/type (mapped to equipment_name column)
        room_equipment: Relationship to RoomEquipment association table
    
    Examples:
        - Projector
        - Whiteboard
        - Conference Phone
        - Smart TV
        - HD Camera
    """    
    __tablename__ = "equipment"
    
    id = Column("equipment_id", Integer, primary_key=True, index=True, autoincrement=True)
    name = Column("equipment_name", String, nullable=False)

    room_equipment = relationship("RoomEquipment", back_populates="equipment", cascade="all, delete-orphan")

    def __init__(self, name:str):
        """
        Initialize a new Equipment.
        
        Args:
            name: Equipment type/name (e.g., "Projector", "Whiteboard")
        """
        super().__init__()
        self.name = name