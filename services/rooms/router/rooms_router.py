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
    user_id=user_id_role['user_id']
    user_role=user_id_role['role']

    if user_role not in [UserRole.admin.value,UserRole.manager.value] or user_id is  None:
        raise HTTPException(status_code=403,detail="Not authorized to perform this action")

@router.post("/create",status_code=201)
async def create_room(request:RoomCreateRequest, db:Session=Depends(get_db), user_id_role:dict[str,str]=Depends(get_current_user)):

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
    check_admin_manager_role(user_id_role)
    
    room:Room|None=(db.query(Room)
                         .options(joinedload(Room.room_equipment))
                         .filter(Room.id==room_id).first())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    equip=db.query(Equipment).filter(Equipment.name==request.equipment.name).all()
    
    room.room_equipment.clear()
    
    equipments=[{"id":eq.id,"quantity":eq2.quantity}
                for eq in equip 
                for eq2 in request.equipment if eq.name==request.equipment.name]
  
    
    for eq in equipments:
        room.room_equipment.append(RoomEquipment(room_id=room_id,equipment_id=eq["id"],quantity=1))
        
        
    room.name=request.name
    room.capacity=request.capacity
    room.location=request.location
    room.status=request.status
    db.commit()
    return {}


@router.delete("/delete{name}",status_code=204)
async def delete_room(name:str, db:Session=Depends(get_db), user_id_role:dict[str,str]=Depends(get_current_user)):

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
            "is_available": room.is_available,
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
            is_available=room["is_available"],
            equipments=[eq["equipment_name"] for eq in room["room_equipment"]]
        )
        for room in rooms_serialized
    ]
    return RoomResponseList(rooms=response)


@router.get("/status/{name}",status_code=200)
async def get_room_status(name:str, db:Session=Depends(get_db), user_id_role:dict[str,str]=Depends(get_current_user)):
    
    
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