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
    Schema for updating existing room details.
    
    Extends RoomCreateRequest with equipment list.
    
    Attributes:
        name: Updated room name
        capacity: Updated capacity
        location: Updated location
        equipments: List of equipment items with quantities
    
    Validation:
        - All validations from RoomCreateRequest
        - Equipment list cannot be empty
    """
    equipments:List[EquipmentCreateRequest]

    @field_validator('equipments')
    @classmethod
    def validate_equipments(cls, value):
        """Ensure at least one equipment item is provided."""
        if not value:
            raise ValueError("Equipments list cannot be empty")
        return value
    
    
    
class RoomResponse(BaseModel):
    """
    Schema for room data in API responses.
    
    Attributes:
        name: Room name
        capacity: Maximum occupancy
        location: Physical location
        is_available: Current availability status
        equipments: List of equipment names in the room
    """
    name: str
    capacity: int
    location: str
    is_available:bool
    equipments:List[str]

class RoomResponseList(BaseModel):
    """
    Schema for list of rooms in API responses.
    
    Used by GET /api/v1/rooms endpoint.
    
    Attributes:
        rooms: Array of room objects
    """
    rooms:List[RoomResponse]