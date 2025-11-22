"""
Custom error handlers and exceptions for Bookings Service.
Provides consistent error responses across all endpoints.

Author: Dana Kossaybati
"""
from fastapi import HTTPException, status

class BookingNotFoundException(HTTPException):
    """
    Exception raised when booking is not found.
    Returns 404 Not Found.
    """
    def __init__(self, booking_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )

class BookingConflictException(HTTPException):
    """
    Exception raised when booking conflicts with existing reservation.
    Returns 409 Conflict.
    """
    def __init__(self, message: str = "Room is already booked for this time slot"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=message
        )

class RoomNotFoundException(HTTPException):
    """
    Exception raised when room doesn't exist (from Rooms service).
    Returns 404 Not Found.
    """
    def __init__(self, room_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found"
        )

class UnauthorizedBookingAccessException(HTTPException):
    """
    Exception raised when user tries to access/modify another user's booking.
    Returns 403 Forbidden.
    """
    def __init__(self, message: str = "You don't have permission to access this booking"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )

class InvalidBookingStateException(HTTPException):
    """
    Exception raised when trying to perform invalid operation on booking.
    For example: updating a cancelled booking, cancelling already cancelled booking.
    Returns 400 Bad Request.
    """
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
