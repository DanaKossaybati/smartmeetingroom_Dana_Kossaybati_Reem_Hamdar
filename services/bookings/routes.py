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
import traceback
from utils import cache_response

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
    Create a new room booking reservation.
    
    Reserves a meeting room for a specified date and time range. The endpoint
    validates all booking constraints and checks for time conflicts with
    existing reservations.
    
    Args:
        booking_data (schemas.BookingCreate): Booking details with fields:
            - room_id (int): ID of room to reserve
            - booking_date (date): Reservation date (cannot be in past)
            - start_time (time): Start time in HH:MM:SS format
            - end_time (time): End time in HH:MM:SS format
            - purpose (str): Meeting description/title
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        schemas.BookingResponse: Created booking with fields:
            - booking_id (int): Unique booking identifier
            - room_id (int): Reserved room ID
            - user_id (int): User who made reservation
            - booking_date (date): Reservation date
            - start_time (time): Reservation start time
            - end_time (time): Reservation end time
            - duration_minutes (int): Total duration
            - purpose (str): Meeting description
            - status (str): Always "confirmed" for new bookings
            - created_at (datetime): Booking creation timestamp
    
    Raises:
        HTTPException(400): Invalid date/time (past date, invalid times, duration out of range)
        HTTPException(404): Room not found
        HTTPException(409): Time slot conflicts with existing booking
        HTTPException(500): Unexpected server error
    
    Validation Rules:
        - booking_date must not be in the past
        - end_time must be strictly after start_time
        - duration must be between 15 minutes (0:15) and 12 hours (12:00)
        - room_id must refer to existing room
        - time slot must not overlap with existing "confirmed" bookings
    
    Example:
        POST /api/bookings/
        Authorization: Bearer <token>
        {
            "room_id": 5,
            "booking_date": "2024-02-15",
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "purpose": "Team standup meeting"
        }
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
        print(f"Error creating booking: {str(e)}")
        traceback.print_exc()
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
    Retrieve bookings with optional filtering.
    
    Gets a list of bookings filtered by optional criteria. Access control is
    enforced: regular users see only their bookings, admins see all bookings.
    
    Args:
        room_id (int, optional): Query parameter to filter by specific room ID
        date (date, optional): Query parameter to filter by date (format: YYYY-MM-DD)
        status (str, optional): Query parameter to filter by status
            Valid values: "confirmed", "cancelled", "pending", "completed"
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        list[schemas.BookingResponse]: List of booking objects. Each contains:
            - booking_id (int): Unique booking identifier
            - room_id (int): Room ID for this booking
            - user_id (int): User who made the booking
            - booking_date (date): Reservation date
            - start_time (time): Reservation start time
            - end_time (time): Reservation end time
            - duration_minutes (int): Total duration in minutes
            - purpose (str): Meeting description
            - status (str): Current status
            - created_at (datetime): Booking creation timestamp
            - updated_at (datetime): Last modification timestamp
    
    Raises:
        HTTPException(500): Unexpected server error
    
    Authorization Rules:
        - Regular users see only their own bookings
        - Admins/facility_managers see all bookings (filtered by query params)
    
    Query Parameter Examples:
        GET /api/bookings/ - Get all user's bookings
        GET /api/bookings/?room_id=5 - Get bookings for room 5
        GET /api/bookings/?date=2024-02-15 - Get bookings on specific date
        GET /api/bookings/?status=confirmed - Get confirmed bookings only
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
    Retrieve a specific booking by ID.
    
    Gets detailed information about a single booking. Access control is enforced:
    users can only view their own bookings unless they are admins or facility managers.
    
    Args:
        booking_id (int): Path parameter - the booking ID to retrieve
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        schemas.BookingResponse: Booking object with fields:
            - booking_id (int): Unique booking identifier
            - room_id (int): Room ID for this booking
            - user_id (int): User who made the booking
            - booking_date (date): Reservation date
            - start_time (time): Reservation start time
            - end_time (time): Reservation end time
            - duration_minutes (int): Total duration in minutes
            - purpose (str): Meeting description
            - status (str): Current status (confirmed, cancelled, pending, completed)
            - created_at (datetime): Booking creation timestamp
            - updated_at (datetime): Last modification timestamp
            - cancelled_at (datetime, optional): Cancellation timestamp if cancelled
    
    Raises:
        HTTPException(404): Booking not found
        HTTPException(403): User lacks permission to view this booking
    
    Authorization Rules:
        - Users can view their own bookings
        - Admins/facility_managers can view any booking
        - Auditors can view any booking
    
    Example:
        GET /api/bookings/42
        Authorization: Bearer <token>
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
    Update an existing booking.
    
    Modifies booking details (time, date, or purpose). Changes are re-validated
    against all booking constraints including time conflict checks.
    
    Args:
        booking_id (int): Path parameter - the booking ID to update
        update_data (schemas.BookingUpdate): Update data with optional fields:
            - booking_date (date, optional): New reservation date
            - start_time (time, optional): New start time
            - end_time (time, optional): New end time
            - purpose (str, optional): New meeting description
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        schemas.BookingResponse: Updated booking object with fields:
            - booking_id (int): The booking ID
            - room_id (int): Room ID
            - user_id (int): Booking owner user ID
            - booking_date (date): Updated reservation date
            - start_time (time): Updated start time
            - end_time (time): Updated end time
            - duration_minutes (int): Updated duration
            - purpose (str): Updated description
            - status (str): Current status
            - updated_at (datetime): Update timestamp
    
    Raises:
        HTTPException(400): Invalid date/time (past date, invalid times, invalid duration)
        HTTPException(403): User lacks permission to update this booking
        HTTPException(404): Booking not found
        HTTPException(409): New time conflicts with existing bookings
    
    Validation Rules:
        - Cannot update cancelled or completed bookings
        - New date cannot be in the past
        - End time must be after start time
        - Duration must remain between 15 minutes and 12 hours
        - New time slot must not conflict with other confirmed bookings
    
    Authorization Rules:
        - Users can update their own bookings
        - Admins/facility_managers can update any booking
    
    Example:
        PUT /api/bookings/42
        Authorization: Bearer <token>
        {
            "start_time": "15:00:00",
            "end_time": "16:00:00",
            "purpose": "Updated meeting agenda"
        }
    
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
    
    Cancels a booking by setting its status to 'cancelled' and recording the
    cancellation timestamp. The record is preserved for audit trail purposes.
    
    Args:
        booking_id (int): Path parameter - the booking ID to cancel
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        dict: Cancellation confirmation with fields:
            - message (str): "Booking cancelled successfully"
            - booking_id (int): The cancelled booking ID
            - cancelled_at (datetime): Cancellation timestamp
    
    Raises:
        HTTPException(400): Booking already cancelled or in invalid state for cancellation
        HTTPException(403): User lacks permission to cancel this booking
        HTTPException(404): Booking not found
    
    Authorization Rules:
        - Users can cancel their own bookings
        - Admins/facility_managers can cancel any booking
    
    Implementation Notes:
        - Uses soft delete (status='cancelled') rather than hard delete
        - Preserves booking record for audit trail and history
        - Records cancellation timestamp in cancelled_at field
        - Cannot cancel already-cancelled or completed bookings
    
    Example:
        DELETE /api/bookings/42
        Authorization: Bearer <token>
        
        Response (200):
        {
            "message": "Booking cancelled successfully",
            "booking_id": 42,
            "cancelled_at": "2024-02-28T10:15:00"
        }
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

@cache_response(expire_seconds=60)
@router.get(
    "/availability/check",
    response_model=schemas.AvailabilityResponse,
    summary="Check room availability",
    description="Verify if room is available for specified time"
)
async def check_availability(
    room_id: int = Query(..., description="Room ID to check"),
    booking_date: date_type = Query(..., description="Date to check (YYYY-MM-DD)"),
    start_time: str = Query(..., description="Start time (HH:MM:SS)"),
    end_time: str = Query(..., description="End time (HH:MM:SS)"),
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check room availability for a specific time slot.
    
    Determines if a room is available for the specified date and time range.
    Results are cached for 60 seconds to reduce database queries.
    
    Args:
        room_id (int): Query parameter - the room ID to check availability for
        booking_date (date): Query parameter - date to check (format: YYYY-MM-DD)
        start_time (str): Query parameter - start time (format: HH:MM:SS)
        end_time (str): Query parameter - end time (format: HH:MM:SS)
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        schemas.AvailabilityResponse: Availability status with fields:
            - available (bool): True if time slot is available, False if booked
            - room_id (int): The checked room ID
            - date (date): The checked date
            - start_time (time): The checked start time
            - end_time (time): The checked end time
            - message (str): "Available" or "Time slot is already booked"
    
    Raises:
        HTTPException(400): Invalid time format or other validation error
        HTTPException(500): Unexpected server error
    
    Query Parameter Examples:
        GET /api/bookings/availability/check?room_id=5&booking_date=2024-2-15&start_time=14:00:00&end_time=15:00:00
    
    Caching:
        - Results cached for 60 seconds
        - Cache key includes room_id, date, and time range
        - Reduces repeated database queries during rapid checking
    """
    try:
        # Parse time strings
        from datetime import time as time_type
        start = time_type.fromisoformat(start_time)
        end = time_type.fromisoformat(end_time)
        
        # Check availability
        is_available = BookingService.check_availability(
            db, room_id, booking_date, start, end
        )
        
        return schemas.AvailabilityResponse(
            available=is_available,
            room_id=room_id,
            date=booking_date,
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
    Get complete schedule for a specific room.
    
    Retrieves all bookings for a room on a specified date, ordered chronologically
    by start time. Useful for viewing available time slots for a room.
    
    Args:
        room_id (int): Path parameter - the room ID to get schedule for
        date (date, optional): Query parameter - date to get schedule for (format: YYYY-MM-DD)
            Defaults to today if not provided
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        list[schemas.BookingResponse]: List of bookings for the room on that date:
            - booking_id (int): Unique booking identifier
            - room_id (int): The requested room ID
            - user_id (int): User who made each booking
            - booking_date (date): Date of booking
            - start_time (time): Booking start time
            - end_time (time): Booking end time
            - duration_minutes (int): Duration of each booking
            - purpose (str): Meeting description
            - status (str): Booking status
            - created_at (datetime): When booking was created
    
    Raises:
        HTTPException(404): Room does not exist
        HTTPException(500): Unexpected server error
    
    Implementation Notes:
        - Results are ordered by start_time (earliest first)
        - Includes only non-cancelled bookings by default
        - Returns empty list if no bookings on that date
    
    Query Parameter Examples:
        GET /api/bookings/room/5/schedule - Get today's schedule for room 5
        GET /api/bookings/room/5/schedule?date=2024-02-15 - Get schedule for specific date
    """    
    try:
        # Default to today if no date provided
        if date is None:
            from datetime import datetime
            date = datetime.now().date()
        
        bookings = BookingService.get_room_schedule(db, room_id, date)
        return bookings
    
    except HTTPException:
        raise
        
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
    Get complete audit trail of changes for a booking.
    
    Retrieves a time-ordered history of all modifications made to a booking,
    including creation, updates, and cancellation. Useful for tracking changes
    and compliance auditing.
    
    Args:
        booking_id (int): Path parameter - the booking ID to get history for
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        list[schemas.BookingHistoryResponse]: List of history records in chronological order:
            - history_id (int): Unique history record identifier
            - booking_id (int): Associated booking ID
            - action (str): Action performed (created, updated, cancelled)
            - changed_by (int): User ID who made the change
            - previous_values (dict): Previous field values
            - new_values (dict): New field values
            - timestamp (datetime): When change was made
            - notes (str): Additional context about the change
    
    Raises:
        HTTPException(403): User lacks permission to view this booking's history
        HTTPException(404): Booking not found
    
    Authorization Rules:
        - Users can view history for their own bookings
        - Admins/facility_managers can view any booking's history
        - Auditors can view any booking's history (read-only)
    
    Example:
        GET /api/bookings/42/history
        Authorization: Bearer <token>
        
        Response (200): [
            {
                "history_id": 101,
                "booking_id": 42,
                "action": "created",
                "changed_by": 1,
                "timestamp": "2024-02-15T10:00:00",
                "notes": "Initial booking creation"
            },
            {
                "history_id": 102,
                "booking_id": 42,
                "action": "updated",
                "changed_by": 1,
                "previous_values": {"start_time": "14:00:00"},
                "new_values": {"start_time": "14:30:00"},
                "timestamp": "2024-02-15T10:30:00",
                "notes": "Time adjustment"
            }
        ]
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
    
    Retrieves the complete booking history for a user. Access control is enforced:
    users can only view their own bookings unless they are admins or facility managers.
    
    Args:
        user_id (int): Path parameter - the user ID to get bookings for
        current_user (dict): Current authenticated user from JWT token (FastAPI dependency)
            Contains: user_id, username, role
        db (Session): SQLAlchemy database session (FastAPI dependency injection)
    
    Returns:
        list[schemas.BookingResponse]: List of all bookings for the user:
            - booking_id (int): Unique booking identifier
            - room_id (int): Room that was booked
            - user_id (int): The requested user ID
            - booking_date (date): Reservation date
            - start_time (time): Reservation start time
            - end_time (time): Reservation end time
            - duration_minutes (int): Total duration
            - purpose (str): Meeting description
            - status (str): Current status (confirmed, cancelled, completed, etc.)
            - created_at (datetime): When booking was created
            - updated_at (datetime): Last modification timestamp
    
    Raises:
        HTTPException(403): User lacks permission to view this user's bookings
    
    Authorization Rules:
        - Users can view their own booking history
        - Admins/facility_managers can view any user's history
    
    Example:
        GET /api/bookings/user/5/history
        Authorization: Bearer <token>
        
        Response (200): [
            {
                "booking_id": 42,
                "room_id": 5,
                "user_id": 5,
                "booking_date": "2024-02-15",
                "start_time": "14:00:00",
                "end_time": "15:30:00",
                "duration_minutes": 90,
                "purpose": "Project planning session",
                "status": "confirmed",
                "created_at": "2024-02-10T10:00:00",
                "updated_at": "2024-02-10T10:00:00"
            }
        ]
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
