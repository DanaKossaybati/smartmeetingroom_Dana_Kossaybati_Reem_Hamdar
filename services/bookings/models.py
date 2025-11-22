"""
SQLAlchemy database models for Bookings Service.
Defines Booking and BookingHistory table structures.

Author: Team Member 1
"""
from sqlalchemy import Column, Integer, String, Date, Time, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class Booking(Base):
    """
    Booking model representing room reservations.
    
    Handles room booking lifecycle: creation, updates, cancellation.
    Includes conflict detection to prevent double-booking.
    
    Attributes:
        booking_id: Primary key, auto-incremented
        user_id: Foreign key to users table (who made the booking)
        room_id: Foreign key to rooms table (which room is booked)
        booking_date: Date of the reservation
        start_time: Reservation start time
        end_time: Reservation end time (must be > start_time)
        status: Booking status (confirmed, pending, cancelled, completed)
        purpose: Optional description of meeting purpose
        created_at: When booking was created
        updated_at: Last modification timestamp
        cancelled_at: When booking was cancelled (null if active)
        cancelled_by: User ID who cancelled (for audit trail)
    """
    __tablename__ = "bookings"
    
    # Primary key - auto-incremented integer
    booking_id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys (not enforced by SQLAlchemy for microservices flexibility)
    # We verify existence through inter-service API calls
    user_id = Column(
        Integer,
        nullable=False,
        index=True  # Indexed for fast "user's bookings" queries
    )
    room_id = Column(
        Integer,
        nullable=False,
        index=True  # Indexed for fast "room schedule" queries
    )
    
    # Booking time information
    booking_date = Column(
        Date,
        nullable=False,
        index=True  # Indexed for date-based queries and conflict detection
    )
    start_time = Column(
        Time,
        nullable=False
    )
    end_time = Column(
        Time,
        nullable=False
        # Note: Database constraint ensures end_time > start_time
    )
    
    # Booking metadata
    status = Column(
        String(20),
        nullable=False,
        default="confirmed",
        index=True  # Indexed for filtering by status
        # Possible values: pending, confirmed, cancelled, completed
    )
    purpose = Column(
        Text,
        nullable=True  # Optional meeting description
    )
    
    # Audit timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()  # PostgreSQL sets this automatically
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()  # Auto-update on any change
    )
    
    # Cancellation tracking (for audit and analytics)
    cancelled_at = Column(
        DateTime(timezone=True),
        nullable=True  # Null if booking is active
    )
    cancelled_by = Column(
        Integer,
        nullable=True  # User ID who cancelled
    )
    
    def __repr__(self):
        """String representation for debugging."""
        return f"<Booking(id={self.booking_id}, room={self.room_id}, date={self.booking_date}, status={self.status})>"


class BookingHistory(Base):
    """
    BookingHistory model for tracking all booking modifications.
    
    Provides complete audit trail of booking lifecycle.
    Records: creation, updates (time changes), cancellations.
    
    Attributes:
        history_id: Primary key
        booking_id: Which booking was modified
        user_id: Original booking owner
        room_id: Which room was booked
        action: Type of change (created, updated, cancelled, completed)
        previous_start_time: Start time before change (for updates)
        previous_end_time: End time before change (for updates)
        new_start_time: Start time after change
        new_end_time: End time after change
        changed_by: User who made the change
        timestamp: When the change occurred
    """
    __tablename__ = "booking_history"
    
    history_id = Column(Integer, primary_key=True, index=True)
    
    # Links to the booking being tracked
    booking_id = Column(
        Integer,
        nullable=False,
        index=True  # Indexed for fast history lookup by booking
    )
    
    # Snapshot of booking state
    user_id = Column(Integer, nullable=False)
    room_id = Column(Integer, nullable=False)
    
    # Type of change that occurred
    action = Column(
        String(20),
        nullable=False
        # Values: 'created', 'updated', 'cancelled', 'completed'
    )
    
    # Previous state (for updates) - null for creation
    previous_start_time = Column(Time, nullable=True)
    previous_end_time = Column(Time, nullable=True)
    
    # New state (null for cancellation/completion)
    new_start_time = Column(Time, nullable=True)
    new_end_time = Column(Time, nullable=True)
    
    # Audit information
    changed_by = Column(
        Integer,
        nullable=True  # User who made the change
    )
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True  # Indexed for time-based queries
    )
    
    def __repr__(self):
        """String representation for debugging."""
        return f"<BookingHistory(booking={self.booking_id}, action={self.action}, time={self.timestamp})>"
