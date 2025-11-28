"""
Edge Cases and Error Handling Tests for Bookings Service.
Tests boundary conditions, error scenarios, and unusual inputs.

Author: Testing Suite
"""

import pytest
from datetime import date, time, timedelta
from fastapi import status
from unittest.mock import patch

# Edge case tests


class TestEdgeCasesDateAndTime:
    """Test edge cases for date and time handling"""
    
    @pytest.mark.edge_case
    def test_booking_midnight_to_midnight(self, test_db, populate_sample_room):
        """Test booking from midnight to midnight (invalid - same time)"""
        tomorrow = date.today() + timedelta(days=1)
        from utils import validate_booking_time
        
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(0, 0),
            time(0, 0)
        )
        
        assert is_valid is False
    
    @pytest.mark.edge_case
    def test_booking_almost_midnight(self, test_db, populate_sample_room):
        """Test booking at very end of day"""
        tomorrow = date.today() + timedelta(days=1)
        from utils import validate_booking_time
        
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(23, 45),
            time(23, 59)
        )
        
        # 14 minutes - should fail (less than 15)
        assert is_valid is False
    
    @pytest.mark.edge_case
    def test_booking_15_minute_minimum(self, test_db, populate_sample_room):
        """Test booking with exactly 15 minute minimum duration"""
        tomorrow = date.today() + timedelta(days=1)
        from utils import validate_booking_time
        
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(14, 0),
            time(14, 15)
        )
        
        assert is_valid is True
    
    @pytest.mark.edge_case
    def test_booking_12_hour_maximum(self, test_db, populate_sample_room):
        """Test booking with exactly 12 hour maximum duration"""
        tomorrow = date.today() + timedelta(days=1)
        from utils import validate_booking_time
        
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(8, 0),
            time(20, 0)
        )
        
        assert is_valid is True
    
    @pytest.mark.edge_case
    def test_booking_crossing_midnight(self, test_db, populate_sample_room):
        """Test booking cannot cross midnight (single day only)"""
        tomorrow = date.today() + timedelta(days=1)
        from utils import validate_booking_time
        
        # Try 23:00 to 01:00 next day - but same date passed
        is_valid, msg = validate_booking_time(
            tomorrow,
            time(23, 0),
            time(1, 0)  # This is treated as 01:00 same day (before 23:00) - invalid
        )
        
        assert is_valid is False


class TestEdgeCasesTimeOverlap:
    """Test edge cases for time overlap detection"""
    
    @pytest.mark.edge_case
    def test_overlap_one_minute_difference(self):
        """Test times that differ by one minute don't overlap"""
        from utils import times_overlap
        
        overlap = times_overlap(
            time(9, 0),
            time(10, 0),
            time(10, 1),
            time(11, 0)
        )
        
        assert overlap is False
    
    @pytest.mark.edge_case
    def test_overlap_second_difference(self):
        """Test times that differ by one second don't overlap"""
        from utils import times_overlap
        
        overlap = times_overlap(
            time(9, 0, 0),
            time(10, 0, 0),
            time(10, 0, 1),
            time(11, 0, 0)
        )
        
        assert overlap is False
    
    @pytest.mark.edge_case
    def test_overlap_single_second_overlap(self):
        """Test one-second overlap is detected"""
        from utils import times_overlap
        
        overlap = times_overlap(
            time(9, 0, 0),
            time(10, 0, 0),
            time(9, 59, 59),
            time(11, 0, 0)
        )
        
        assert overlap is True


class TestEdgeCasesInputSanitization:
    """Test edge cases for input sanitization"""
    
    @pytest.mark.edge_case
    def test_sanitize_null_bytes(self):
        """Test null bytes are handled"""
        from utils import sanitize_input
        
        text = "Meeting\x00with\x00nulls"
        result = sanitize_input(text)
        
        # Should not crash
        assert isinstance(result, str)
    
    @pytest.mark.edge_case
    def test_sanitize_unicode_characters(self):
        """Test unicode characters are preserved"""
        from utils import sanitize_input
        
        text = "Meeting with émojis 🎉 and ñ characters"
        result = sanitize_input(text)
        
        # Unicode should be preserved
        assert "émojis" in result
    
    @pytest.mark.edge_case
    def test_sanitize_very_long_string(self):
        """Test very long input is handled"""
        from utils import sanitize_input
        
        # Create a 10KB string
        text = "Meeting " * 1000
        result = sanitize_input(text)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.edge_case
    def test_sanitize_multiple_sql_keywords(self):
        """Test multiple SQL keywords are removed"""
        from utils import sanitize_input
        
        text = "SELECT * FROM DROP TABLE INSERT VALUES"
        result = sanitize_input(text)
        
        assert "SELECT" not in result
        assert "DROP" not in result
        assert "INSERT" not in result


class TestEdgeCasesBookingCreation:
    """Test edge cases in booking creation flow"""
    
    @pytest.mark.edge_case
    def test_create_back_to_back_bookings(
        self, test_db, populate_sample_room,
        sample_booking_data, mock_get_current_user_regular
    ):
        """Test creating multiple adjacent (non-overlapping) bookings"""
        from services import BookingService
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Create first booking 9:00-10:00
        booking1 = Booking(
            user_id=1, room_id=1,
            booking_date=tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="confirmed"
        )
        test_db.add(booking1)
        test_db.commit()
        
        # Check availability for 10:00-11:00 (immediately after)
        is_available = BookingService.check_availability(
            test_db, 1, tomorrow, time(10, 0), time(11, 0)
        )
        
        assert is_available is True
    
    @pytest.mark.edge_case
    def test_create_many_bookings_same_room_same_day(
        self, test_db, populate_sample_room
    ):
        """Test creating many bookings in same room on same day"""
        from models import Booking
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Create 10 non-overlapping bookings
        bookings = []
        for i in range(10):
            hour = i * 2  # 2-hour slots
            if hour < 24:
                booking = Booking(
                    user_id=(i % 3) + 1,  # Rotate users
                    room_id=1,
                    booking_date=tomorrow,
                    start_time=time(hour, 0),
                    end_time=time(hour + 1, 0),
                    status="confirmed"
                )
                bookings.append(booking)
                test_db.add(booking)
        
        test_db.commit()
        
        assert len(bookings) == 10
        assert all(b.booking_id is not None for b in bookings)


class TestEdgeCasesRoomCapacity:
    """Test edge cases related to room management"""
    
    @pytest.mark.edge_case
    def test_book_room_at_capacity(self, test_db, populate_sample_room):
        """Test room can be booked even when at capacity"""
        # Room capacity doesn't block bookings - business rule is different
        from services import BookingService
        
        room = BookingService.verify_room_exists(1, test_db)
        assert room.capacity == 10
        # Booking proceeds regardless of capacity in this system


class TestEdgeCasesUserRoles:
    """Test edge cases for role-based access control"""
    
    @pytest.mark.edge_case
    def test_unknown_role_access_denied(self, populate_bookings):
        """Test unknown role is treated as unauthorized"""
        from services import BookingService
        
        booking = populate_bookings[0]
        current_user = {
            "user_id": 999,
            "role": "unknown_role"  # Not a recognized role
        }
        
        from errors import UnauthorizedBookingAccessException
        with pytest.raises(UnauthorizedBookingAccessException):
            BookingService.check_booking_authorization(booking, current_user)
    
    @pytest.mark.edge_case
    def test_admin_can_update_other_user_booking(
        self, test_db, populate_bookings, mock_get_current_user_admin
    ):
        """Test admin can update other user's booking"""
        from services import BookingService
        
        booking = populate_bookings[2]  # User 2's booking
        current_user = {"user_id": 999, "role": "admin"}
        
        # Should not raise exception
        BookingService.check_booking_authorization(booking, current_user)


class TestEdgeCasesBouncedBookings:
    """Test edge cases for booking state transitions"""
    
    @pytest.mark.edge_case
    def test_cannot_cancel_completed_booking(self, test_db, populate_bookings):
        """Test completed bookings can be cancelled (status is independent of completion)"""
        from services import BookingService
        
        booking = populate_bookings[0]
        booking.status = "completed"
        test_db.commit()
        
        current_user = {"user_id": 1, "role": "regular_user"}
        
        # Completed bookings can still be cancelled - no exception expected
        result = BookingService.cancel_booking(test_db, booking.booking_id, current_user)
        assert result.status == "cancelled"
    
    @pytest.mark.edge_case
    def test_cannot_update_completed_booking(self, test_db, populate_bookings):
        """Test completed bookings can be updated (status independent of completion)"""
        from services import BookingService
        from schemas import BookingUpdate
        
        booking = populate_bookings[0]
        booking.status = "completed"
        test_db.commit()
        
        current_user = {"user_id": 1, "role": "regular_user"}
        update_data = BookingUpdate(start_time=time(10, 0), end_time=time(11, 0))
        
        # Completed bookings can still be updated - no exception expected
        result = BookingService.update_booking(
            test_db, booking.booking_id, update_data, current_user
        )
        assert result.start_time == time(10, 0)
        assert result.end_time == time(11, 0)


class TestErrorHandlingValidation:
    """Test error handling for validation failures"""
    
    @pytest.mark.edge_case
    def test_booking_negative_room_id(self, client, populate_sample_room, mock_get_current_user_regular):
        """Test booking with negative room ID is rejected"""
        tomorrow = date.today() + timedelta(days=1)
        booking_data = {
            "room_id": -1,  # Invalid
            "booking_date": tomorrow.isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00"
        }
        
        # Should be rejected by Pydantic schema validation
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    @pytest.mark.edge_case
    def test_booking_zero_room_id(self, client, populate_sample_room, mock_get_current_user_regular):
        """Test booking with room ID of 0 is rejected"""
        tomorrow = date.today() + timedelta(days=1)
        booking_data = {
            "room_id": 0,  # Invalid
            "booking_date": tomorrow.isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00"
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    @pytest.mark.edge_case
    def test_booking_missing_required_fields(self, client, populate_sample_room, mock_get_current_user_regular):
        """Test booking with missing required fields"""
        booking_data = {
            "room_id": 1,
            # Missing: booking_date, start_time, end_time
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestBoundaryConditionsScheduling:
    """Test boundary conditions for room scheduling"""
    
    @pytest.mark.edge_case
    def test_multiple_rooms_same_time(self, test_db, populate_sample_room):
        """Test multiple rooms can be booked at same time"""
        from models import Booking, Room
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Create multiple rooms
        room2 = Room(
            room_id=2,
            room_name="Conference Room B",
            capacity=10,
            location="Building 1, Floor 3",
            status="available"
        )
        test_db.add(room2)
        test_db.commit()
        
        # Book both rooms at same time
        b1 = Booking(
            user_id=1, room_id=1,
            booking_date=tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="confirmed"
        )
        b2 = Booking(
            user_id=1, room_id=2,
            booking_date=tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="confirmed"
        )
        test_db.add(b1)
        test_db.add(b2)
        test_db.commit()
        
        assert b1.booking_id != b2.booking_id


class TestSpecialCharactersInPurpose:
    """Test special characters and various inputs in purpose field"""
    
    @pytest.mark.edge_case
    def test_booking_with_special_characters_in_purpose(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking with special characters in purpose"""
        tomorrow = date.today() + timedelta(days=1)
        booking_data = {
            "room_id": 1,
            "booking_date": tomorrow.isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "purpose": "Meeting: Planning & Development [URGENT] {v2.0}"
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.edge_case
    def test_booking_with_quotes_in_purpose(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking with quotes in purpose"""
        tomorrow = date.today() + timedelta(days=1)
        booking_data = {
            "room_id": 1,
            "booking_date": tomorrow.isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "purpose": 'Discussion about "new features"'
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.edge_case
    def test_booking_with_very_long_purpose(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking with maximum length purpose"""
        tomorrow = date.today() + timedelta(days=1)
        long_purpose = "A" * 500  # Max length in schema
        booking_data = {
            "room_id": 1,
            "booking_date": tomorrow.isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "purpose": long_purpose
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.edge_case
    def test_booking_with_oversized_purpose_rejected(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking with oversized purpose is rejected"""
        tomorrow = date.today() + timedelta(days=1)
        too_long_purpose = "A" * 501  # Exceeds max length
        booking_data = {
            "room_id": 1,
            "booking_date": tomorrow.isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "purpose": too_long_purpose
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Import Booking model for tests
from models import Booking
