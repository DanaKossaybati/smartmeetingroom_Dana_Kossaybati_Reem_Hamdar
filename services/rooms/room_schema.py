"""
Pydantic schemas for Rooms Service request/response validation.
Defines data models for API endpoints with automatic validation.

Author: Reem Hamdar
"""
from typing import List

from pydantic import BaseModel, field_validator, Field


class RoomCreateRequest(BaseModel):
    """
    Schema for creating a new room.
    
    Attributes:
        name: Unique room name
        capacity: Maximum number of people (must be positive)
        location: Physical location of the room
    
    Validation:
        - Capacity must be a positive integer
    """
    name: str=Field(...,description="Room name")
    capacity: int=Field(...,description="Room capacity")
    location: str=Field(...,description="Room location")
    


    @field_validator('capacity')
    @classmethod
    def validate_capacity(cls, value):
        """Ensure capacity is a positive number."""
        if value <= 0:
            raise ValueError("Capacity must be a positive integer")
        return value
    
class EquipmentCreateRequest(BaseModel):
    """
    Schema for equipment items when creating/updating rooms.
    
    Attributes:
        name: Equipment name (e.g., "Projector", "Whiteboard")
        quantity: Number of units
    """
    name:str
    quantity:int
    
class RoomUpdateRequest(RoomCreateRequest):
    """
    Schema for updating an existing room.
    
    Extends RoomCreateRequest with additional fields for status and equipment.
    
    Attributes:
        name: Updated room name
        capacity: Updated capacity
        location: Updated location
        status: Room availability status ('available', 'unavailable', 'maintenance')
        equipments: List of equipment assignments
    
    Validation:
        - Status must be one of: 'available', 'unavailable', 'maintenance'
        - Equipments list cannot be empty if provided
    """
    status: str = 'available'  # Add status field with default value
    equipments:List[EquipmentCreateRequest] = []

    @field_validator('status')
    @classmethod
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ['available', 'unavailable', 'maintenance']
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

    @field_validator('equipments')
    @classmethod
    def validate_equipments(cls, value):
        """Ensure equipments list is not empty if provided."""
        if not value:
            raise ValueError("Equipments list cannot be empty")
        return value
    
    
    
class RoomResponse(BaseModel):
    """
    Schema for room response data.
    
    Attributes:
        name: Room name
        capacity: Maximum occupancy
        location: Physical location
        status: Current availability status
        equipments: List of equipment names available in the room
    
    Validation:
        - Status must be one of: 'available', 'unavailable', 'maintenance'
    """    
    name: str
    capacity: int
    location: str
    status: str  # Changed from is_available (bool) to status (string: 'available', 'unavailable', 'maintenance')
    equipments:List[str]

    @field_validator('status')
    @classmethod
    def validate_status(cls, value):
        """Ensure status is valid."""
        valid_statuses = ['available', 'unavailable', 'maintenance']
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

class RoomResponseList(BaseModel):
    """
    Schema for list of rooms response.
    
    Attributes:
        rooms: List of RoomResponse objects
    """    
    rooms:List[RoomResponse]