"""
Business logic layer for Bookings Service.
Handles all booking operations independently of HTTP layer.

This follows the Service Layer pattern:
- Routes handle HTTP (request/response)
- Services handle business logic
- Models handle data persistence

Author: Dana Kossaybati
"""
from sqlalchemy.orm import Session
from datetime import datetime, date as date_type, time as time_type
from typing import Optional, List
import httpx
import os

from models import Booking, Room, BookingHistory
import schemas
from utils import sanitize_input, validate_booking_time, times_overlap
from errors import (
    BookingNotFoundException,
    BookingConflictException,
    RoomNotFoundException,
    UnauthorizedBookingAccessException,
    InvalidBookingStateException
)

# Environment variables for inter-service communication
ROOMS_SERVICE_URL = os.getenv("ROOMS_SERVICE_URL", "http://localhost:8002")

class BookingService:
    """
    Service class containing all booking-related business logic.
    Keeps routes thin and business logic testable.
    """
    
    @staticmethod
    def verify_room_exists(room_id: int, db: Session) -> Room:
        """
        Verify room exists and is available for booking.
        Queries rooms table directly (shared database approach).
        
        Args:
            room_id: Room identifier to verify
            db: Database session
            
        Returns:
            Room object if exists and available
            
        Raises:
            RoomNotFoundException: If room doesn't exist or unavailable
        """
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room:
            raise RoomNotFoundException(f"Room with ID {room_id} not found")
        
        # Check room status - only 'available' rooms can be booked
        if room.status != 'available':
            raise RoomNotFoundException(
                f"Room '{room.room_name}' is currently {room.status} and cannot be booked"
            )
        
        return room
    
    @staticmethod
    def check_booking_conflict(
        db: Session,
        room_id: int,
        booking_date: date_type,
        start_time: time_type,
        end_time: time_type,
        exclude_booking_id: Optional[int] = None
    ) -> bool:
        """
        Check if proposed booking conflicts with existing reservations.
        
        Conflict detection algorithm:
        1. Find all confirmed/pending bookings for same room and date
        2. Check if proposed time overlaps with any existing booking
        3. Exclude specific booking (for update operations)
        
        Args:
            db: Database session
            room_id: Room to check
            booking_date: Date to check
            start_time: Proposed start time
            end_time: Proposed end time
            exclude_booking_id: Booking ID to exclude (for updates)
        
        Returns:
            True if conflict exists, False if time slot is available
        
        Performance note:
            Query is optimized with indexes on (room_id, booking_date, status)
        """
        # Query for potentially conflicting bookings
        query = db.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.booking_date == booking_date,
            # Only check active bookings (not cancelled)
            Booking.status.in_(['confirmed', 'pending'])
        )
        
        # Exclude specific booking (for update operations)
        if exclude_booking_id:
            query = query.filter(Booking.booking_id != exclude_booking_id)
        
        # Get all potentially conflicting bookings
        existing_bookings = query.all()
        
        # Check each existing booking for time overlap
        for booking in existing_bookings:
            if times_overlap(
                start_time, end_time,
                booking.start_time, booking.end_time
            ):
                # Conflict found!
                return True
        
        # No conflicts found
        return False
    
    @staticmethod
    def log_booking_history(
        db: Session,
        booking_id: int,
        user_id: int,
        room_id: int,
        action: str,
        changed_by: int,
        prev_start: Optional[time_type] = None,
        prev_end: Optional[time_type] = None,
        new_start: Optional[time_type] = None,
        new_end: Optional[time_type] = None
    ):
        """
        Log booking changes to history table for audit trail.
        
        Creates immutable record of all booking modifications.
        Useful for: debugging, accountability, analytics, compliance.
        
        Args:
            db: Database session
            booking_id: Booking being modified
            user_id: Original booking owner
            room_id: Room being booked
            action: Type of change (created, updated, cancelled, completed)
            changed_by: User making the change
            prev_start: Previous start time (for updates)
            prev_end: Previous end time (for updates)
            new_start: New start time (for updates/creation)
            new_end: New end time (for updates/creation)
        """
        try:
            history_record = BookingHistory(
                booking_id=booking_id,
                user_id=user_id,
                room_id=room_id,
                action=action,
                previous_start_time=prev_start,
                previous_end_time=prev_end,
                new_start_time=new_start,
                new_end_time=new_end,
                changed_by=changed_by,
                timestamp=datetime.utcnow()
            )
            db.add(history_record)
            db.commit()
        except Exception as e:
            # Log error but don't fail the main operation
            # History is important but not critical
            print(f"Warning: Failed to log booking history: {e}")
            db.rollback()
    
    @staticmethod
    async def create_booking(
        db: Session,
        booking_data: schemas.BookingCreate,
        current_user: dict
    ) -> Booking:
        """
        Create a new room booking.
        
        Business logic pipeline:
        1. Validate date/time constraints
        2. Verify room exists
        3. Check for conflicts with existing bookings
        4. Create booking record
        5. Log to history table
        
        Args:
            db: Database session
            booking_data: Booking creation data
            current_user: Authenticated user making the booking
        
        Returns:
            Created Booking model instance
        
        Raises:
            ValueError: If time/date validation fails
            RoomNotFoundException: If room doesn't exist
            BookingConflictException: If time slot is already booked
        """
        # Step 1: Validate date and time constraints
        is_valid, error_msg = validate_booking_time(
            booking_data.booking_date,
            booking_data.start_time,
            booking_data.end_time
        )
        if not is_valid:
            raise ValueError(error_msg)
        
        # Step 2: Verify room exists
        room_exists = BookingService.verify_room_exists(booking_data.room_id, db)
        if not room_exists:
            raise RoomNotFoundException(booking_data.room_id)
        
        # Step 3: Check for booking conflicts
        has_conflict = BookingService.check_booking_conflict(
            db,
            booking_data.room_id,
            booking_data.booking_date,
            booking_data.start_time,
            booking_data.end_time
        )
        if has_conflict:
            raise BookingConflictException()
        
        # Step 4: Create booking record
        # Sanitize purpose text (defense in depth)
        purpose = sanitize_input(booking_data.purpose) if booking_data.purpose else None
        
        new_booking = Booking(
            user_id=current_user["user_id"],
            room_id=booking_data.room_id,
            booking_date=booking_data.booking_date,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            purpose=purpose,
            status="confirmed",  # Auto-confirm (no approval workflow)
            created_at=datetime.utcnow()
        )
        
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)  # Get auto-generated fields
        
        # Step 5: Log to history table
        BookingService.log_booking_history(
            db,
            booking_id=new_booking.booking_id,
            user_id=current_user["user_id"],
            room_id=booking_data.room_id,
            action="created",
            changed_by=current_user["user_id"],
            new_start=booking_data.start_time,
            new_end=booking_data.end_time
        )
        
        return new_booking
    
    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int) -> Booking:
        """
        Retrieve booking by ID.
        
        Args:
            db: Database session
            booking_id: Booking ID to retrieve
        
        Returns:
            Booking model instance
        
        Raises:
            BookingNotFoundException: If booking doesn't exist
        """
        booking = db.query(Booking).filter(
            Booking.booking_id == booking_id
        ).first()
        
        if not booking:
            raise BookingNotFoundException(booking_id)
        
        return booking
    
    @staticmethod
    def get_user_bookings(
        db: Session,
        user_id: int,
        status: Optional[str] = None
    ) -> List[Booking]:
        """
        Get all bookings for a specific user.
        
        Args:
            db: Database session
            user_id: User ID to filter by
            status: Optional status filter (confirmed, cancelled, etc.)
        
        Returns:
            List of Booking models
        """
        query = db.query(Booking).filter(
            Booking.user_id == user_id
        )
        
        if status:
            query = query.filter(Booking.status == status)
        
        # Order by date (newest first)
        bookings = query.order_by(
            Booking.booking_date.desc(),
            Booking.start_time.desc()
        ).all()
        
        return bookings
    
    @staticmethod
    def get_all_bookings(
        db: Session,
        room_id: Optional[int] = None,
        date: Optional[date_type] = None,
        status: Optional[str] = None
    ) -> List[Booking]:
        """
        Get all bookings with optional filters.
        
        Used by admins/facility managers to view all bookings.
        
        Args:
            db: Database session
            room_id: Optional room filter
            date: Optional date filter
            status: Optional status filter
        
        Returns:
            List of Booking models
        """
        query = db.query(Booking)
        
        # Apply filters
        if room_id:
            query = query.filter(Booking.room_id == room_id)
        if date:
            query = query.filter(Booking.booking_date == date)
        if status:
            query = query.filter(Booking.status == status)
        
        # Order by date and time
        bookings = query.order_by(
            Booking.booking_date.desc(),
            Booking.start_time.desc()
        ).all()
        
        return bookings
    
    @staticmethod
    def update_booking(
        db: Session,
        booking_id: int,
        update_data: schemas.BookingUpdate,
        current_user: dict
    ) -> Booking:
        """
        Update existing booking.
        
        Business logic:
        1. Get existing booking
        2. Verify authorization
        3. Check booking state (can't update cancelled bookings)
        4. Validate new times if provided
        5. Check for conflicts with new times
        6. Update booking
        7. Log to history
        
        Args:
            db: Database session
            booking_id: Booking to update
            update_data: Fields to update
            current_user: User making the change
        
        Returns:
            Updated Booking model
        
        Raises:
            BookingNotFoundException: If booking doesn't exist
            UnauthorizedBookingAccessException: If user lacks permission
            InvalidBookingStateException: If booking can't be updated
            BookingConflictException: If new times conflict
        """
        # Get existing booking
        booking = BookingService.get_booking_by_id(db, booking_id)
        
        # Check authorization
        BookingService.check_booking_authorization(booking, current_user)
        
        # Check if booking can be updated
        if booking.status == "cancelled":
            raise InvalidBookingStateException("Cannot update cancelled booking")
        
        # Store old values for history
        old_start = booking.start_time
        old_end = booking.end_time
        
        # Update times if provided
        if update_data.start_time or update_data.end_time:
            new_start = update_data.start_time or booking.start_time
            new_end = update_data.end_time or booking.end_time
            
            # Validate new time range
            is_valid, error_msg = validate_booking_time(
                booking.booking_date,
                new_start,
                new_end
            )
            if not is_valid:
                raise ValueError(error_msg)
            
            # Check for conflicts with new times
            has_conflict = BookingService.check_booking_conflict(
                db,
                booking.room_id,
                booking.booking_date,
                new_start,
                new_end,
                exclude_booking_id=booking_id  # Exclude self from conflict check
            )
            if has_conflict:
                raise BookingConflictException(
                    "New time slot conflicts with existing booking"
                )
            
            booking.start_time = new_start
            booking.end_time = new_end
        
        # Update purpose if provided
        if update_data.purpose is not None:
            booking.purpose = sanitize_input(update_data.purpose)
        
        # Update timestamp
        booking.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(booking)
        
        # Log to history
        BookingService.log_booking_history(
            db,
            booking_id=booking.booking_id,
            user_id=booking.user_id,
            room_id=booking.room_id,
            action="updated",
            changed_by=current_user["user_id"],
            prev_start=old_start,
            prev_end=old_end,
            new_start=booking.start_time,
            new_end=booking.end_time
        )
        
        return booking
    
    @staticmethod
    def cancel_booking(
        db: Session,
        booking_id: int,
        current_user: dict
    ) -> Booking:
        """
        Cancel a booking (soft delete).
        
        Changes status to 'cancelled' rather than deleting record.
        Preserves booking data for audit trail and analytics.
        
        Args:
            db: Database session
            booking_id: Booking to cancel
            current_user: User cancelling the booking
        
        Returns:
            Cancelled Booking model
        
        Raises:
            BookingNotFoundException: If booking doesn't exist
            UnauthorizedBookingAccessException: If user lacks permission
            InvalidBookingStateException: If booking already cancelled
        """
        # Get booking
        booking = BookingService.get_booking_by_id(db, booking_id)
        
        # Check authorization
        BookingService.check_booking_authorization(booking, current_user)
        
        # Check if already cancelled
        if booking.status == "cancelled":
            raise InvalidBookingStateException("Booking is already cancelled")
        
        # Update status (soft delete)
        booking.status = "cancelled"
        booking.cancelled_at = datetime.utcnow()
        booking.cancelled_by = current_user["user_id"]
        booking.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(booking)
        
        # Log to history
        BookingService.log_booking_history(
            db,
            booking_id=booking.booking_id,
            user_id=booking.user_id,
            room_id=booking.room_id,
            action="cancelled",
            changed_by=current_user["user_id"]
        )
        
        return booking
    
    @staticmethod
    def check_availability(
        db: Session,
        room_id: int,
        booking_date: date_type,
        start_time: time_type,
        end_time: time_type
    ) -> bool:
        """
        Check if room is available for specified time slot.
        
        Args:
            db: Database session
            room_id: Room to check
            booking_date: Date to check
            start_time: Proposed start time
            end_time: Proposed end time
        
        Returns:
            True if available, False if conflicts exist
        """
        return not BookingService.check_booking_conflict(
            db, room_id, booking_date, start_time, end_time
        )
    
    @staticmethod
    def get_room_schedule(
        db: Session,
        room_id: int,
        date: date_type
    ) -> List[Booking]:
        """
        Get all bookings for a room on specific date.
        
        Returns bookings ordered by start time (chronological).
        
        Args:
            db: Database session
            room_id: Room ID
            date: Date to get schedule for
        
        Returns:
            List of Booking models for that room and date
        """
        # Step 1: Verify room exists
        room_exists = BookingService.verify_room_exists(room_id, db)
        if not room_exists:
            raise RoomNotFoundException(room_id)
        
        bookings = db.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.booking_date == date,
            # Only show active bookings (not cancelled)
            Booking.status.in_(['confirmed', 'pending', 'completed'])
        ).order_by(Booking.start_time).all()
        
        return bookings
    
    @staticmethod
    def get_booking_history(
        db: Session,
        booking_id: int
    ) -> List[BookingHistory]:
        """
        Get complete history of changes for a booking.
        
        Args:
            db: Database session
            booking_id: Booking ID
        
        Returns:
            List of BookingHistory records (newest first)
        """
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking_id
        ).order_by(BookingHistory.timestamp.desc()).all()
        
        return history
    
    @staticmethod
    def check_booking_authorization(
        booking: Booking,
        current_user: dict
    ):
        """
        Check if user is authorized to access/modify booking.
        
        Authorization rules:
        - User can access their own bookings
        - Admins can access any booking
        - Facility managers can access any booking
        
        Args:
            booking: Booking to check
            current_user: Current authenticated user
        
        Raises:
            UnauthorizedBookingAccessException: If access denied
        """
        # Allow if user owns the booking
        if booking.user_id == current_user["user_id"]:
            return
        
        # Allow if user is admin or facility manager
        if current_user["role"] in ["admin", "facility_manager"]:
            return
        
        # Otherwise, deny access
        raise UnauthorizedBookingAccessException()
