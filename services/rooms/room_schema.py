from typing import List

from pydantic import BaseModel, field_validator, Field


class RoomCreateRequest(BaseModel):
    name: str=Field(...,description="Room name")
    capacity: int=Field(...,description="Room capacity")
    location: str=Field(...,description="Room location")
    


    @field_validator('capacity')
    @classmethod
    def validate_capacity(cls, value):
        if value <= 0:
            raise ValueError("Capacity must be a positive integer")
        return value
    
class EquipmentCreateRequest(BaseModel):
    name:str
    quantity:int
    
class RoomUpdateRequest(RoomCreateRequest):
    equipments:List[EquipmentCreateRequest]

    @field_validator('equipments')
    @classmethod
    def validate_equipments(cls, value):
        if not value:
            raise ValueError("Equipments list cannot be empty")
        return value
    
    
    
class RoomResponse(BaseModel):    
    name: str
    capacity: int
    location: str
    is_available:bool
    equipments:List[str]

class RoomResponseList(BaseModel):    
    rooms:List[RoomResponse]