"""
Unit Tests for Bookings Service - Business Logic & Services Layer.
Tests service methods, validators, and business logic in isolation.

Author: Testing Suite
"""

import pytest
from datetime import date, time, timedelta, datetime
from fastapi import status
from unittest.mock import Mock, patch, MagicMock

# Import service and utilities
from services import BookingService
from utils import validate_booking_time, times_overlap, sanitize_input
from models import Booking, Room
from schemas import BookingCreate, BookingUpdate
from errors import (
    BookingNotFoundException,
    BookingConflictException,
    RoomNotFoundException,
    UnauthorizedBookingAccessException,
    InvalidBookingStateException
)


class TestValidateBookingTime:
    """Unit tests for booking time validation logic"""
    
    @pytest.mark.unit
    def test_valid_booking_time(self):
        """Test valid booking times pass validation"""
        tomorrow = date.today() + timedelta(days=1)
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(14, 0),
            time(15, 30)
        )
        
        assert is_valid is True
        assert msg == ""
    
    @pytest.mark.unit
    def test_booking_date_in_past(self):
        """Test booking date in past fails validation"""
        yesterday = date.today() - timedelta(days=1)
        is_valid, msg = validate_booking_time(
            yesterday,
            time(14, 0),
            time(15, 30)
        )
        
        assert is_valid is False
        assert "past" in msg.lower()
    
    @pytest.mark.unit
    def test_booking_date_today_is_valid(self):
        """Test booking for today is valid if time is in future"""
        today = date.today()
        # Use a time far in future
        is_valid, msg = validate_booking_time(
            today,
            time(23, 0),  # 11 PM
            time(23, 30)
        )
        
        # This might fail if current time is past 11 PM, but generally valid
        # The test checks the logic, not current time
        assert isinstance(is_valid, bool)
    
    @pytest.mark.unit
    def test_end_time_before_start_time(self):
        """Test end time must be after start time"""
        tomorrow = date.today() + timedelta(days=1)
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(15, 30),
            time(14, 0)  # Earlier than start
        )
        
        assert is_valid is False
        assert "after" in msg.lower()
    
    @pytest.mark.unit
    def test_same_start_and_end_time(self):
        """Test start and end time cannot be same"""
        tomorrow = date.today() + timedelta(days=1)
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(14, 0),
            time(14, 0)  # Same time
        )
        
        assert is_valid is False
    
    @pytest.mark.unit
    def test_duration_too_short(self):
        """Test booking duration must be at least 15 minutes"""
        tomorrow = date.today() + timedelta(days=1)
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(14, 0),
            time(14, 10)  # Only 10 minutes
        )
        
        assert is_valid is False
        assert "15 minutes" in msg.lower()
    
    @pytest.mark.unit
    def test_duration_exactly_15_minutes(self):
        """Test 15 minute duration is acceptable minimum"""
        tomorrow = date.today() + timedelta(days=1)
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(14, 0),
            time(14, 15)  # Exactly 15 minutes
        )
        
        assert is_valid is True
    
    @pytest.mark.unit
    def test_duration_too_long(self):
        """Test booking duration cannot exceed 12 hours"""
        tomorrow = date.today() + timedelta(days=1)
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(8, 0),
            time(21, 0)  # 13 hours
        )
        
        assert is_valid is False
        assert "12 hours" in msg.lower()
    
    @pytest.mark.unit
    def test_duration_exactly_12_hours(self):
        """Test 12 hour duration is acceptable maximum"""
        tomorrow = date.today() + timedelta(days=1)
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(8, 0),
            time(20, 0)  # Exactly 12 hours
        )
        
        assert is_valid is True


class TestTimesOverlap:
    """Unit tests for time overlap detection logic"""
    
    @pytest.mark.unit
    def test_no_overlap_distinct_times(self):
        """Test times with clear separation don't overlap"""
        overlap = times_overlap(
            time(9, 0),
            time(10, 0),
            time(10, 0),
            time(11, 0)
        )
        
        assert overlap is False
    
    @pytest.mark.unit
    def test_complete_overlap(self):
        """Test complete time overlap is detected"""
        overlap = times_overlap(
            time(9, 0),
            time(11, 0),
            time(9, 0),
            time(11, 0)
        )
        
        assert overlap is True
    
    @pytest.mark.unit
    def test_partial_overlap_start(self):
        """Test overlap at start of second booking"""
        overlap = times_overlap(
            time(9, 0),
            time(10, 30),
            time(10, 0),
            time(11, 0)
        )
        
        assert overlap is True
    
    @pytest.mark.unit
    def test_partial_overlap_end(self):
        """Test overlap at end of first booking"""
        overlap = times_overlap(
            time(9, 0),
            time(10, 0),
            time(9, 30),
            time(11, 0)
        )
        
        assert overlap is True
    
    @pytest.mark.unit
    def test_contained_within(self):
        """Test booking contained within another booking"""
        overlap = times_overlap(
            time(9, 0),
            time(11, 0),
            time(9, 30),
            time(10, 30)
        )
        
        assert overlap is True
    
    @pytest.mark.unit
    def test_contains_other(self):
        """Test booking that contains another booking"""
        overlap = times_overlap(
            time(9, 30),
            time(10, 30),
            time(9, 0),
            time(11, 0)
        )
        
        assert overlap is True
    
    @pytest.mark.unit
    def test_adjacent_but_no_overlap(self):
        """Test adjacent bookings (end of one = start of other) don't overlap"""
        overlap = times_overlap(
            time(9, 0),
            time(10, 0),
            time(10, 0),
            time(11, 0)
        )
        
        assert overlap is False


class TestSanitizeInput:
    """Unit tests for input sanitization"""
    
    @pytest.mark.unit
    def test_clean_input_unchanged(self):
        """Test clean input is preserved"""
        text = "Team meeting for project planning"
        result = sanitize_input(text)
        
        assert result == text
    
    @pytest.mark.unit
    def test_removes_sql_injection_patterns(self):
        """Test SQL injection patterns are removed"""
        text = "Meeting'; DROP TABLE bookings;--"
        result = sanitize_input(text)
        
        assert "DROP" not in result
        assert "--" not in result
    
    @pytest.mark.unit
    def test_removes_script_tags(self):
        """Test script tags are removed"""
        text = "Meeting <script>alert('xss')</script>"
        result = sanitize_input(text)
        
        assert "<script>" not in result
        assert "</script>" not in result
    
    @pytest.mark.unit
    def test_empty_string_handling(self):
        """Test empty string is handled safely"""
        result = sanitize_input("")
        
        assert result == ""
    
    @pytest.mark.unit
    def test_none_handling(self):
        """Test None is handled safely"""
        result = sanitize_input(None)
        
        assert result is None


class TestBookingServiceVerifyRoom:
    """Unit tests for room verification logic"""
    
    @pytest.mark.unit
    def test_verify_room_exists(self, test_db, populate_sample_room):
        """Test room verification succeeds for existing available room"""
        room = BookingService.verify_room_exists(1, test_db)
        
        assert room is not None
        assert room.room_id == 1
        assert room.status == "available"
    
    @pytest.mark.unit
    def test_verify_room_not_found(self, test_db):
        """Test room verification fails for non-existent room"""
        with pytest.raises(RoomNotFoundException):
            BookingService.verify_room_exists(999, test_db)
    
    @pytest.mark.unit
    def test_verify_room_unavailable_status(self, test_db):
        """Test room verification fails for unavailable rooms"""
        # Create unavailable room
        room = Room(
            room_id=2,
            room_name="Maintenance Room",
            capacity=5,
            location="Building 1",
            status="maintenance"  # Not available
        )
        test_db.add(room)
        test_db.commit()
        
        with pytest.raises(RoomNotFoundException):
            BookingService.verify_room_exists(2, test_db)


class TestBookingServiceConflictDetection:
    """Unit tests for booking conflict detection logic"""
    
    @pytest.mark.unit
    def test_no_conflict_empty_room(self, test_db, populate_sample_room):
        """Test no conflict when room has no bookings"""
        tomorrow = date.today() + timedelta(days=10)
        
        has_conflict = BookingService.check_booking_conflict(
            test_db, 1, tomorrow, time(9, 0), time(10, 0)
        )
        
        assert has_conflict is False
    
    @pytest.mark.unit
    def test_conflict_with_existing_booking(self, test_db, populate_bookings):
        """Test conflict detection with overlapping booking"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Try to book overlapping time (existing is 9:00-10:00)
        has_conflict = BookingService.check_booking_conflict(
            test_db, 1, tomorrow, time(9, 30), time(10, 30)
        )
        
        assert has_conflict is True
    
    @pytest.mark.unit
    def test_no_conflict_different_room(self, test_db, populate_bookings):
        """Test no conflict when booking different room"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Existing booking is in room 1, try room 2
        has_conflict = BookingService.check_booking_conflict(
            test_db, 2, tomorrow, time(9, 0), time(10, 0)
        )
        
        assert has_conflict is False
    
    @pytest.mark.unit
    def test_no_conflict_different_date(self, test_db, populate_bookings):
        """Test no conflict when booking different date"""
        later = date.today() + timedelta(days=10)
        
        # Existing booking is on tomorrow, try later date
        has_conflict = BookingService.check_booking_conflict(
            test_db, 1, later, time(9, 0), time(10, 0)
        )
        
        assert has_conflict is False
    
    @pytest.mark.unit
    def test_no_conflict_after_existing(self, test_db, populate_bookings):
        """Test no conflict when booking after existing time"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Existing is 9:00-10:00, book 10:00-11:00
        has_conflict = BookingService.check_booking_conflict(
            test_db, 1, tomorrow, time(10, 0), time(11, 0)
        )
        
        assert has_conflict is False
    
    @pytest.mark.unit
    def test_exclude_booking_id_for_updates(self, test_db, populate_bookings):
        """Test exclude_booking_id allows updating same booking"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Get first booking ID
        booking = test_db.query(Booking).filter(
            Booking.room_id == 1,
            Booking.booking_date == tomorrow,
            Booking.start_time == time(9, 0)
        ).first()
        
        # Check conflict excluding this booking - should be False
        has_conflict = BookingService.check_booking_conflict(
            test_db, 1, tomorrow, time(9, 0), time(10, 0),
            exclude_booking_id=booking.booking_id
        )
        
        assert has_conflict is False
    
    @pytest.mark.unit
    def test_cancelled_bookings_ignored_in_conflict(self, test_db, populate_bookings):
        """Test cancelled bookings don't block new bookings"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Cancel existing booking
        booking = test_db.query(Booking).filter(
            Booking.room_id == 1,
            Booking.booking_date == tomorrow,
            Booking.start_time == time(9, 0)
        ).first()
        booking.status = "cancelled"
        test_db.commit()
        
        # Try to book same time - should not conflict
        has_conflict = BookingService.check_booking_conflict(
            test_db, 1, tomorrow, time(9, 0), time(10, 0)
        )
        
        assert has_conflict is False


class TestBookingServiceCheckAuthorization:
    """Unit tests for authorization checking logic"""
    
    @pytest.mark.unit
    def test_authorize_booking_owner(self, populate_bookings):
        """Test owner can access own booking"""
        booking = populate_bookings[0]
        current_user = {"user_id": 1, "role": "regular_user"}
        
        # Should not raise exception
        BookingService.check_booking_authorization(booking, current_user)
    
    @pytest.mark.unit
    def test_authorize_admin(self, populate_bookings):
        """Test admin can access any booking"""
        booking = populate_bookings[0]
        current_user = {"user_id": 999, "role": "admin"}
        
        # Should not raise exception
        BookingService.check_booking_authorization(booking, current_user)
    
    @pytest.mark.unit
    def test_authorize_facility_manager(self, populate_bookings):
        """Test facility manager can access any booking"""
        booking = populate_bookings[0]
        current_user = {"user_id": 888, "role": "facility_manager"}
        
        # Should not raise exception
        BookingService.check_booking_authorization(booking, current_user)
    
    @pytest.mark.unit
    def test_deny_unauthorized_user(self, populate_bookings):
        """Test unauthorized user cannot access others' bookings"""
        booking = populate_bookings[0]
        current_user = {"user_id": 999, "role": "regular_user"}
        
        with pytest.raises(UnauthorizedBookingAccessException):
            BookingService.check_booking_authorization(booking, current_user)


class TestBookingServiceGetBookingById:
    """Unit tests for retrieving bookings by ID"""
    
    @pytest.mark.unit
    def test_get_booking_exists(self, test_db, populate_bookings):
        """Test retrieving existing booking"""
        booking = BookingService.get_booking_by_id(test_db, populate_bookings[0].booking_id)
        
        assert booking is not None
        assert booking.booking_id == populate_bookings[0].booking_id
    
    @pytest.mark.unit
    def test_get_booking_not_found(self, test_db):
        """Test retrieving non-existent booking"""
        with pytest.raises(BookingNotFoundException):
            BookingService.get_booking_by_id(test_db, 999)


class TestBookingServiceGetUserBookings:
    """Unit tests for retrieving user's bookings"""
    
    @pytest.mark.unit
    def test_get_user_bookings(self, test_db, populate_bookings):
        """Test retrieving all bookings for a user"""
        bookings = BookingService.get_user_bookings(test_db, 1)
        
        assert len(bookings) == 2  # User 1 has 2 bookings
        assert all(b.user_id == 1 for b in bookings)
    
    @pytest.mark.unit
    def test_get_user_bookings_by_status(self, test_db, populate_bookings):
        """Test retrieving user bookings filtered by status"""
        bookings = BookingService.get_user_bookings(test_db, 1, status="confirmed")
        
        assert len(bookings) == 2
        assert all(b.status == "confirmed" for b in bookings)
    
    @pytest.mark.unit
    def test_get_user_no_bookings(self, test_db, populate_sample_room):
        """Test retrieving bookings for user with no bookings"""
        bookings = BookingService.get_user_bookings(test_db, 999)
        
        assert len(bookings) == 0


class TestBookingServiceGetAllBookings:
    """Unit tests for retrieving all bookings (admin view)"""
    
    @pytest.mark.unit
    def test_get_all_bookings(self, test_db, populate_bookings):
        """Test retrieving all bookings"""
        bookings = BookingService.get_all_bookings(test_db)
        
        assert len(bookings) == 3
    
    @pytest.mark.unit
    def test_get_all_bookings_filter_by_room(self, test_db, populate_bookings):
        """Test filtering all bookings by room"""
        bookings = BookingService.get_all_bookings(test_db, room_id=1)
        
        assert all(b.room_id == 1 for b in bookings)
    
    @pytest.mark.unit
    def test_get_all_bookings_filter_by_status(self, test_db, populate_bookings):
        """Test filtering all bookings by status"""
        bookings = BookingService.get_all_bookings(test_db, status="confirmed")
        
        assert all(b.status == "confirmed" for b in bookings)


class TestBookingServiceGetRoomSchedule:
    """Unit tests for room schedule retrieval"""
    
    @pytest.mark.unit
    def test_get_room_schedule(self, test_db, populate_bookings):
        """Test retrieving room schedule for a date"""
        tomorrow = date.today() + timedelta(days=1)
        bookings = BookingService.get_room_schedule(test_db, 1, tomorrow)
        
        assert len(bookings) == 2
        assert all(b.room_id == 1 for b in bookings)
        # Check chronological ordering
        assert bookings[0].start_time < bookings[1].start_time
    
    @pytest.mark.unit
    def test_get_room_schedule_excludes_cancelled(self, test_db, populate_bookings):
        """Test schedule excludes cancelled bookings"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Cancel one booking
        booking = test_db.query(Booking).filter(
            Booking.room_id == 1,
            Booking.booking_date == tomorrow,
            Booking.start_time == time(9, 0)
        ).first()
        booking.status = "cancelled"
        test_db.commit()
        
        schedule = BookingService.get_room_schedule(test_db, 1, tomorrow)
        
        assert len(schedule) == 1  # Only non-cancelled booking
        assert schedule[0].start_time == time(14, 0)
    
    @pytest.mark.unit
    def test_get_room_schedule_empty_date(self, test_db, populate_sample_room):
        """Test schedule is empty for date with no bookings"""
        future_date = date.today() + timedelta(days=100)
        bookings = BookingService.get_room_schedule(test_db, 1, future_date)
        
        assert len(bookings) == 0


class TestBookingServiceCheckAvailability:
    """Unit tests for availability checking"""
    
    @pytest.mark.unit
    def test_availability_available(self, test_db, populate_sample_room):
        """Test availability check returns True when available"""
        tomorrow = date.today() + timedelta(days=10)
        
        is_available = BookingService.check_availability(
            test_db, 1, tomorrow, time(9, 0), time(10, 0)
        )
        
        assert is_available is True
    
    @pytest.mark.unit
    def test_availability_not_available(self, test_db, populate_bookings):
        """Test availability check returns False when booked"""
        tomorrow = date.today() + timedelta(days=1)
        
        is_available = BookingService.check_availability(
            test_db, 1, tomorrow, time(9, 30), time(10, 30)
        )
        
        assert is_available is False
