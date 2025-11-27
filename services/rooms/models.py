import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func


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
