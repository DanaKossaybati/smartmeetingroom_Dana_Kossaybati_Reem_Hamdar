"""
API route handlers for Bookings Service.
Routes are kept thin - they only handle HTTP concerns.
All business logic is delegated to the service layer.

Author: Dana Kossaybati
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date as date_type

import schemas
import auth
from database import get_db
from services import BookingService
from errors import (
    BookingNotFoundException,
    BookingConflictException,
    RoomNotFoundException,
    UnauthorizedBookingAccessException,
    InvalidBookingStateException
)

# Create router with prefix and tags for documentation
router = APIRouter(
    prefix="/api/bookings",
    tags=["bookings"],
    responses={404: {"description": "Not found"}}
)

@router.post(
    "/",
    response_model=schemas.BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new booking",
    description="Reserve a room for specified date and time"
)
async def create_booking(
    booking_data: schemas.BookingCreate,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new room booking.
    
    **Validation:**
    - Date cannot be in the past
    - End time must be after start time
    - Duration between 15 minutes and 12 hours
    - Room must exist
    - Time slot must not conflict with existing bookings
    
    **Returns:**
    - 201: Booking created successfully
    - 400: Invalid date/time
    - 404: Room not found
    - 409: Time slot already booked
    """
    try:
        # Delegate to service layer
        new_booking = await BookingService.create_booking(
            db, booking_data, current_user
        )
        return new_booking
    
    except ValueError as e:
        # Validation errors (date/time)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except (RoomNotFoundException, BookingConflictException) as e:
        # Re-raise HTTP exceptions as-is
        raise e
    
    except Exception as e:
        # Unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating booking"
        )

@router.get(
    "/",
    response_model=List[schemas.BookingResponse],
    summary="Get bookings",
    description="Retrieve bookings (users see own, admins see all)"
)
async def get_bookings(
    room_id: Optional[int] = Query(None, description="Filter by room ID"),
    date: Optional[date_type] = Query(None, description="Filter by date"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get bookings with optional filters.
    
    **Authorization:**
    - Regular users see only their own bookings
    - Admins/facility managers see all bookings
    
    **Query Parameters:**
    - room_id: Filter by specific room
    - date: Filter by specific date (YYYY-MM-DD)
    - status: Filter by status (confirmed, cancelled, pending, completed)
    
    **Returns:**
    - 200: List of bookings
    """
    try:
        # Determine which bookings user can see
        if current_user["role"] in ["admin", "facility_manager"]:
            # Admin/manager sees all bookings with filters
            bookings = BookingService.get_all_bookings(
                db, room_id=room_id, date=date, status=status
            )
        else:
            # Regular user sees only their bookings
            bookings = BookingService.get_user_bookings(
                db, current_user["user_id"], status=status
            )
        
        return bookings
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/{booking_id}",
    response_model=schemas.BookingResponse,
    summary="Get booking by ID",
    description="Retrieve specific booking details"
)
async def get_booking(
    booking_id: int,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific booking by ID.
    
    **Authorization:**
    - Users can view their own bookings
    - Admins/facility managers can view any booking
    
    **Returns:**
    - 200: Booking details
    - 403: Access denied
    - 404: Booking not found
    """
    try:
        # Get booking
        booking = BookingService.get_booking_by_id(db, booking_id)
        
        # Check authorization
        BookingService.check_booking_authorization(booking, current_user)
        
        return booking
    
    except (BookingNotFoundException, UnauthorizedBookingAccessException) as e:
        raise e

@router.put(
    "/{booking_id}",
    response_model=schemas.BookingResponse,
    summary="Update booking",
    description="Modify booking times or purpose"
)
async def update_booking(
    booking_id: int,
    update_data: schemas.BookingUpdate,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update existing booking.
    
    **Updateable fields:**
    - start_time: New start time
    - end_time: New end time
    - purpose: Updated meeting description
    
    **Validation:**
    - Cannot update cancelled bookings
    - New times must not conflict with other bookings
    - End time must be after start time
    
    **Authorization:**
    - Users can update their own bookings
    - Admins/facility managers can update any booking
    
    **Returns:**
    - 200: Booking updated successfully
    - 400: Invalid update (cancelled booking, invalid times)
    - 403: Access denied
    - 404: Booking not found
    - 409: New time conflicts with existing booking
    """
    try:
        updated_booking = BookingService.update_booking(
            db, booking_id, update_data, current_user
        )
        return updated_booking
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except (
        BookingNotFoundException,
        UnauthorizedBookingAccessException,
        InvalidBookingStateException,
        BookingConflictException
    ) as e:
        raise e

@router.delete(
    "/{booking_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel booking",
    description="Cancel a booking (soft delete)"
)
async def cancel_booking(
    booking_id: int,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a booking (soft delete).
    
    Sets status to 'cancelled' rather than deleting record.
    
    **Authorization:**
    - Users can cancel their own bookings
    - Admins/facility managers can cancel any booking
    
    **Returns:**
    - 200: Booking cancelled successfully
    - 400: Booking already cancelled
    - 403: Access denied
    - 404: Booking not found
    """
    try:
        cancelled_booking = BookingService.cancel_booking(
            db, booking_id, current_user
        )
        
        return {
            "message": "Booking cancelled successfully",
            "booking_id": booking_id,
            "cancelled_at": cancelled_booking.cancelled_at
        }
    
    except (
        BookingNotFoundException,
        UnauthorizedBookingAccessException,
        InvalidBookingStateException
    ) as e:
        raise e

@router.get(
    "/availability/check",
    response_model=schemas.AvailabilityResponse,
    summary="Check room availability",
    description="Verify if room is available for specified time"
)
async def check_availability(
    room_id: int = Query(..., description="Room ID to check"),
    date: date_type = Query(..., description="Date to check (YYYY-MM-DD)"),
    start_time: str = Query(..., description="Start time (HH:MM:SS)"),
    end_time: str = Query(..., description="End time (HH:MM:SS)"),
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if room is available for specified time slot.
    
    **Query Parameters:**
    - room_id: Room to check
    - date: Date (YYYY-MM-DD)
    - start_time: Start time (HH:MM:SS)
    - end_time: End time (HH:MM:SS)
    
    **Returns:**
    - 200: Availability status
    """
    try:
        # Parse time strings
        from datetime import time as time_type
        start = time_type.fromisoformat(start_time)
        end = time_type.fromisoformat(end_time)
        
        # Check availability
        is_available = BookingService.check_availability(
            db, room_id, date, start, end
        )
        
        return schemas.AvailabilityResponse(
            available=is_available,
            room_id=room_id,
            date=date,
            start_time=start,
            end_time=end,
            message="Available" if is_available else "Time slot is already booked"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time format: {str(e)}"
        )

@router.get(
    "/room/{room_id}/schedule",
    response_model=List[schemas.BookingResponse],
    summary="Get room schedule",
    description="Get all bookings for a room on specific date"
)
async def get_room_schedule(
    room_id: int,
    date: Optional[date_type] = Query(None, description="Date (defaults to today)"),
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get schedule for specific room.
    
    Returns all bookings for the room on specified date,
    ordered chronologically by start time.
    
    **Returns:**
    - 200: List of bookings for that room and date
    """
    try:
        # Default to today if no date provided
        if date is None:
            from datetime import datetime
            date = datetime.now().date()
        
        bookings = BookingService.get_room_schedule(db, room_id, date)
        return bookings
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/{booking_id}/history",
    response_model=List[schemas.BookingHistoryResponse],
    summary="Get booking history",
    description="Get audit trail of booking modifications"
)
async def get_booking_history(
    booking_id: int,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete history of changes for a booking.
    
    Shows audit trail: creation, updates, cancellation.
    
    **Authorization:**
    - Users can view their own booking history
    - Admins/facility managers/auditors can view any booking history
    
    **Returns:**
    - 200: List of history records (newest first)
    - 403: Access denied
    - 404: Booking not found
    """
    try:
        # Get booking to check authorization
        booking = BookingService.get_booking_by_id(db, booking_id)
        
        # Check authorization (allow auditors too)
        if (current_user["role"] not in ["admin", "facility_manager", "auditor"] and 
            booking.user_id != current_user["user_id"]):
            raise UnauthorizedBookingAccessException()
        
        # Get history
        history = BookingService.get_booking_history(db, booking_id)
        return history
    
    except (BookingNotFoundException, UnauthorizedBookingAccessException) as e:
        raise e

@router.get(
    "/user/{user_id}/history",
    response_model=List[schemas.BookingResponse],
    summary="Get user booking history",
    description="Get all bookings for a specific user"
)
async def get_user_booking_history(
    user_id: int,
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all bookings for a specific user.
    
    **Authorization:**
    - Users can view their own history
    - Admins/facility managers can view any user's history
    
    **Returns:**
    - 200: List of user's bookings
    - 403: Access denied
    """
    try:
        # Check authorization
        if (current_user["role"] not in ["admin", "facility_manager"] and 
            current_user["user_id"] != user_id):
            raise UnauthorizedBookingAccessException(
                "You can only view your own booking history"
            )
        
        bookings = BookingService.get_user_bookings(db, user_id)
        return bookings
    
    except UnauthorizedBookingAccessException as e:
        raise e
