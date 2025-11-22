"""
Pydantic schemas for request/response validation in Bookings Service.
These schemas validate incoming data and structure API responses.

Author: Dana Kossaybati
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, time, datetime

class BookingCreate(BaseModel):
    """
    Schema for creating a new booking.
    Validates all required fields before reservation is created.
    """
    room_id: int = Field(
        ...,
        gt=0,
        description="Room ID to book (must be positive integer)"
    )
    booking_date: date = Field(
        ...,
        description="Date of reservation (YYYY-MM-DD)"
    )
    start_time: time = Field(
        ...,
        description="Start time (HH:MM:SS)"
    )
    end_time: time = Field(
        ...,
        description="End time (HH:MM:SS, must be after start_time)"
    )
    purpose: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional meeting purpose/description"
    )
    
    @field_validator('end_time')
    @classmethod
    def validate_time_order(cls, v, info):
        """
        Ensure end_time is after start_time.
        Pydantic validator runs before business logic.
        """
        # Access start_time from values context
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('End time must be after start time')
        return v

class BookingUpdate(BaseModel):
    """
    Schema for updating existing booking.
    All fields are optional (partial update supported).
    """
    start_time: Optional[time] = Field(
        None,
        description="New start time"
    )
    end_time: Optional[time] = Field(
        None,
        description="New end time"
    )
    purpose: Optional[str] = Field(
        None,
        max_length=500,
        description="Updated meeting purpose"
    )

class BookingResponse(BaseModel):
    """
    Schema for booking data in API responses.
    Matches database model structure.
    """
    booking_id: int
    user_id: int
    room_id: int
    booking_date: date
    start_time: time
    end_time: time
    status: str
    purpose: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    
    class Config:
        # Allow ORM model to be converted to Pydantic model
        from_attributes = True

class AvailabilityCheck(BaseModel):
    """
    Schema for checking room availability.
    Used as query parameters in GET request.
    """
    room_id: int = Field(..., gt=0)
    date: date
    start_time: time
    end_time: time

class AvailabilityResponse(BaseModel):
    """
    Schema for availability check response.
    Indicates if time slot is available and provides context.
    """
    available: bool = Field(
        ...,
        description="True if room is available, False if conflicts exist"
    )
    room_id: int
    date: date
    start_time: time
    end_time: time
    message: Optional[str] = Field(
        None,
        description="Additional information about availability"
    )

class BookingHistoryResponse(BaseModel):
    """
    Schema for booking history records.
    Shows audit trail of booking modifications.
    """
    history_id: int
    booking_id: int
    action: str
    previous_start_time: Optional[time]
    previous_end_time: Optional[time]
    new_start_time: Optional[time]
    new_end_time: Optional[time]
    changed_by: Optional[int]
    timestamp: datetime
    
    class Config:
        from_attributes = True
