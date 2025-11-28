"""
API route handlers for Rooms Service.
Handles room management operations including CRUD operations,
filtering, and availability checks.

Routes are kept thin - they only handle HTTP concerns.
Business logic and data access are delegated to appropriate layers.

Author: Reem Hamdar
"""
from typing import Optional

from aiocache.serializers import JsonSerializer
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from auth import get_current_user
from enums import UserRole
from models import Room, Equipment, RoomEquipment
from room_schema import RoomCreateRequest, RoomUpdateRequest, RoomResponseList, RoomResponse
from aiocache import Cache

router=APIRouter(
    prefix="/api/v1/rooms",
    tags=["rooms"]
)
cache=Cache(Cache.MEMORY,serializer=JsonSerializer())

def check_admin_manager_role(user_id_role:dict[str,str]):
    """
    Verify user has admin or facility manager role.
    
    Helper function to enforce role-based access control for
    room management operations.
    
    Args:
        user_id_role: Dictionary containing 'user_id' and 'role' keys
    
    Raises:
        HTTPException: 403 if user lacks required permissions
    """
    user_id=user_id_role['user_id']
    user_role=user_id_role['role']

    if user_role not in [UserRole.admin.value,UserRole.manager.value] or user_id is  None:
        raise HTTPException(status_code=403,detail="Not authorized to perform this action")

@router.post("/create",status_code=201)
async def create_room(request:RoomCreateRequest, db:Session=Depends(get_db), user_id_role:dict[str,str]=Depends(get_current_user)):
    """
    Create a new meeting room.
    
    Requires admin or facility_manager role.
    
    Args:
        request: Room creation data (name, capacity, location)
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        Empty dict on success
    
    Raises:
        HTTPException: 403 if unauthorized, 400 if invalid details
    """
    check_admin_manager_role(user_id_role)
    
    room= Room(request.name,request.capacity,request.location)
    if not room:
        raise HTTPException(status_code=400,detail="Invalid room details")
    db.add(room)
    db.commit()
    return {}
    
@router.put("/update{room_id}",status_code=204)
async def update_room(room_id:int, request:RoomUpdateRequest,
                      db:Session=Depends(get_db), user_id_role:dict[str,str]=Depends(get_current_user)):
    """
    Update an existing room's details and equipment.
    
    Requires admin or facility_manager role.
    
    Args:
        room_id: ID of the room to update
        request: Updated room data (name, capacity, location, status, equipments)
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        Empty dict on success
    
    Raises:
        HTTPException: 403 if unauthorized, 404 if room not found
    """
    check_admin_manager_role(user_id_role)
    
    room:Room|None=(db.query(Room)
                         .options(joinedload(Room.room_equipment))
                         .filter(Room.id==room_id).first())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Clear existing equipment
    room.room_equipment.clear()
    
    # Add new equipment if provided
    if request.equipments:
        for equipment_req in request.equipments:
            # Find equipment by name
            equipment = db.query(Equipment).filter(Equipment.name == equipment_req.name).first()
            if equipment:
                # Add room-equipment relationship
                room.room_equipment.append(
                    RoomEquipment(
                        room_id=room_id,
                        equipment_id=equipment.id,
                        quantity=equipment_req.quantity
                    )
                )
    
    # Update room details
    room.name = request.name
    room.capacity = request.capacity
    room.location = request.location
    room.is_available = request.status
    db.commit()
    return {}


@router.delete("/delete/{name}",status_code=204)
async def delete_room(name:str, db:Session=Depends(get_db), user_id_role:dict[str,str]=Depends(get_current_user)):
    """
    Delete a room by name.
    
    Requires admin or facility_manager role.
    Cascades to remove all associated equipment.
    
    Args:
        name: Name of the room to delete
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        Empty dict on success
    
    Raises:
        HTTPException: 403 if unauthorized, 404 if room not found
    """
    check_admin_manager_role(user_id_role)
    
    room:Room|None=(db.query(Room)
                         .filter(Room.name==name).first())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    # bookings relationship removed - managed by bookings_service
    room.room_equipment.clear()
    db.delete(room)
    db.commit()
    return {}


@router.get("", response_model=RoomResponseList, status_code=200)
async def get_available_rooms(
        capacity: Optional[int] = None,
        location: Optional[str] = None,
        equipment: Optional[str] = None,
        db: Session = Depends(get_db),
        user_id_role: dict[str, str] = Depends(get_current_user)
):
    """
    Get list of available rooms with optional filtering.
    
    Supports filtering by capacity, location, and equipment.
    Results are cached for 5 minutes per user.
    
    Args:
        capacity: Minimum capacity required (optional)
        location: Room location filter (optional)
        equipment: Equipment name filter (optional)
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        RoomResponseList: List of rooms matching the filters
    
    Caching:
        - Cache key: rooms:{user_id}
        - TTL: 300 seconds (5 minutes)
    """
    user_id = user_id_role['user_id']
    cached_rooms = await cache.get(f"rooms:{user_id}")

    if cached_rooms:
        rooms_serialized = cached_rooms
    else:
        query = db.query(Room).options(joinedload(Room.room_equipment).joinedload(RoomEquipment.equipment))

        if capacity is not None:
            query = query.filter(Room.capacity >= capacity)

        if location is not None:
            query = query.filter(Room.location == location)

        if equipment is not None:
            query = query.join(Room.room_equipment).join(RoomEquipment.equipment).filter(Equipment.name == equipment)

        rooms = query.all()
        rooms_serialized = [{
            "id": room.id,
            "name": room.name,
            "capacity": room.capacity,
            "location": room.location,
            "status": room.is_available,  # Changed from is_available to status
            "room_equipment": [{"equipment_name": re.equipment.name} for re in room.room_equipment]
        } for room in rooms]
        await cache.set(f"rooms:{user_id}", rooms_serialized, ttl=300)
    if not rooms_serialized:
        return RoomResponseList(rooms=[])
    response = [
        RoomResponse(
            name=room["name"],
            capacity=room["capacity"],
            location=room["location"],
            status=room["status"],  # Changed from is_available to status
            equipments=[eq["equipment_name"] for eq in room["room_equipment"]]
        )
        for room in rooms_serialized
    ]
    return RoomResponseList(rooms=response)


@router.get("/status/{name}",status_code=200)
async def get_room_status(name:str, db:Session=Depends(get_db), user_id_role:dict[str,str]=Depends(get_current_user)):
    """
    Get availability status of a specific room.
    
    Returns the current status (available/unavailable/maintenance) of a room by name.
    Results are cached for 5 minutes per user.
    
    Args:
        name: Name of the room to check
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        dict: {"status": str} - current room status
    
    Raises:
        HTTPException: 404 if room not found
    
    Caching:
        - Cache key: status:{user_id}
        - TTL: 300 seconds (5 minutes)
    """
    user_id=user_id_role['user_id']

    cached_status = await cache.get(f"status:{user_id}")
    if cached_status:
     status=cached_status
    else:
     room:Room|None=(db.query(Room)
                         .filter(Room.name==name).first())
     if not room:
            raise HTTPException(status_code=404, detail="Room not found")
     status=room.is_available
    await cache.set(f"status:{user_id}", status, ttl=300)
    return {"status":status}