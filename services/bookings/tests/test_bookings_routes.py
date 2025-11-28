"""
Integration Tests for Bookings Service - API Routes & Endpoints.
Tests full HTTP request/response cycle with real FastAPI client.

Author: Testing Suite
"""

import pytest
from datetime import date, time, timedelta
from fastapi import status
from unittest.mock import patch, MagicMock
import json

# These are API-level tests - test through client, not direct function calls


class TestHealthEndpoints:
    """Test service health check endpoints"""
    
    @pytest.mark.integration
    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["service"] == "bookings"
        assert data["status"] == "running"
    
    @pytest.mark.integration
    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "bookings"


class TestCreateBooking:
    """Test booking creation endpoint (POST /api/bookings/)"""
    
    @pytest.mark.integration
    def test_create_booking_success(
        self, client, test_db, populate_sample_room,
        sample_booking_data, mock_get_current_user_regular
    ):
        """Test successful booking creation"""
        response = client.post(
            "/api/bookings/",
            json=sample_booking_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["room_id"] == sample_booking_data["room_id"]
        assert data["purpose"] == sample_booking_data["purpose"]
        assert data["status"] == "confirmed"
        assert "booking_id" in data
        assert "created_at" in data
    
    @pytest.mark.integration
    def test_create_booking_missing_token(self, client, sample_booking_data):
        """Test booking creation without authentication token"""
        response = client.post(
            "/api/bookings/",
            json=sample_booking_data
        )
        
        # Should return 403 Forbidden (OAuth2 error)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
    
    @pytest.mark.integration
    def test_create_booking_past_date(
        self, client, test_db, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking creation with past date fails"""
        yesterday = date.today() - timedelta(days=1)
        booking_data = {
            "room_id": 1,
            "booking_date": yesterday.isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "purpose": "Past meeting"
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "past" in response.json()["detail"].lower()
    
    @pytest.mark.integration
    def test_create_booking_invalid_time_order(
        self, client, test_db, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking with end time before start time fails"""
        tomorrow = date.today() + timedelta(days=1)
        booking_data = {
            "room_id": 1,
            "booking_date": tomorrow.isoformat(),
            "start_time": "15:30:00",
            "end_time": "14:00:00",
            "purpose": "Invalid times"
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    @pytest.mark.integration
    def test_create_booking_room_not_found(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking creation with non-existent room fails"""
        tomorrow = date.today() + timedelta(days=1)
        booking_data = {
            "room_id": 999,  # Non-existent room
            "booking_date": tomorrow.isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "purpose": "Invalid room"
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.integration
    def test_create_booking_time_conflict(
        self, client, test_db, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test booking creation with conflicting time slot fails"""
        tomorrow = date.today() + timedelta(days=1)
        # Try to book overlapping time (existing is 9:00-10:00)
        booking_data = {
            "room_id": 1,
            "booking_date": tomorrow.isoformat(),
            "start_time": "09:30:00",
            "end_time": "10:30:00",
            "purpose": "Conflicting meeting"
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_409_CONFLICT
    
    @pytest.mark.integration
    def test_create_booking_short_duration(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking with duration < 15 minutes fails"""
        tomorrow = date.today() + timedelta(days=1)
        booking_data = {
            "room_id": 1,
            "booking_date": tomorrow.isoformat(),
            "start_time": "14:00:00",
            "end_time": "14:10:00",  # Only 10 minutes
            "purpose": "Too short"
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.integration
    def test_create_booking_long_duration(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test booking with duration > 12 hours fails"""
        tomorrow = date.today() + timedelta(days=1)
        booking_data = {
            "room_id": 1,
            "booking_date": tomorrow.isoformat(),
            "start_time": "08:00:00",
            "end_time": "21:00:00",  # 13 hours
            "purpose": "Too long"
        }
        
        response = client.post("/api/bookings/", json=booking_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestGetBookings:
    """Test GET /api/bookings/ endpoint"""
    
    @pytest.mark.integration
    def test_get_user_bookings(
        self, client, test_db, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test regular user can view their own bookings"""
        response = client.get("/api/bookings/")
        
        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        assert len(bookings) == 2  # User 1 has 2 bookings
        assert all(b["user_id"] == 1 for b in bookings)
    
    @pytest.mark.integration
    def test_get_all_bookings_as_admin(
        self, client, populate_bookings,
        mock_get_current_user_admin
    ):
        """Test admin can view all bookings"""
        response = client.get("/api/bookings/")
        
        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        assert len(bookings) >= 3  # Sees all bookings
    
    @pytest.mark.integration
    def test_get_bookings_filter_by_status(
        self, client, test_db, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test filtering bookings by status"""
        response = client.get("/api/bookings/?status=confirmed")
        
        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        assert all(b["status"] == "confirmed" for b in bookings)
    
    @pytest.mark.integration
    def test_get_bookings_no_auth(self, client):
        """Test GET bookings without auth fails"""
        response = client.get("/api/bookings/")
        
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]


class TestGetBookingById:
    """Test GET /api/bookings/{booking_id} endpoint"""
    
    @pytest.mark.integration
    def test_get_booking_owner(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test user can view their own booking"""
        booking_id = populate_bookings[0].booking_id
        
        response = client.get(f"/api/bookings/{booking_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["booking_id"] == booking_id
        assert data["user_id"] == 1
    
    @pytest.mark.integration
    def test_get_booking_not_owner_forbidden(
        self, client, populate_bookings,
        mock_get_current_user_regular, monkeypatch
    ):
        """Test user cannot view other's booking"""
        booking_id = populate_bookings[2].booking_id  # User 2's booking
        
        response = client.get(f"/api/bookings/{booking_id}")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.integration
    def test_get_booking_admin_can_view(
        self, client, populate_bookings,
        mock_get_current_user_admin
    ):
        """Test admin can view any booking"""
        booking_id = populate_bookings[2].booking_id  # User 2's booking
        
        response = client.get(f"/api/bookings/{booking_id}")
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.integration
    def test_get_booking_not_found(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test getting non-existent booking fails"""
        response = client.get("/api/bookings/999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateBooking:
    """Test PUT /api/bookings/{booking_id} endpoint"""
    
    @pytest.mark.integration
    def test_update_booking_time(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test updating booking times"""
        booking_id = populate_bookings[0].booking_id
        update_data = {
            "start_time": "09:30:00",
            "end_time": "10:30:00"
        }
        
        response = client.put(
            f"/api/bookings/{booking_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["start_time"] == "09:30:00"
        assert data["end_time"] == "10:30:00"
    
    @pytest.mark.integration
    def test_update_booking_purpose(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test updating booking purpose"""
        booking_id = populate_bookings[0].booking_id
        update_data = {"purpose": "Updated meeting purpose"}
        
        response = client.put(
            f"/api/bookings/{booking_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["purpose"] == "Updated meeting purpose"
    
    @pytest.mark.integration
    def test_update_booking_conflict(
        self, client, test_db, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test updating booking to conflicting time fails"""
        tomorrow = date.today() + timedelta(days=1)
        booking_id = populate_bookings[0].booking_id  # 9:00-10:00
        # Try to move to 14:00-15:30 slot (which has existing booking for user 1)
        update_data = {
            "start_time": "14:00:00",
            "end_time": "15:30:00"
        }
        
        response = client.put(
            f"/api/bookings/{booking_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
    
    @pytest.mark.integration
    def test_update_booking_not_found(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test updating non-existent booking fails"""
        update_data = {"start_time": "09:00:00"}
        
        response = client.put(
            "/api/bookings/999",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.integration
    def test_update_booking_not_owner(
        self, client, populate_bookings,
        mock_get_current_user_regular, monkeypatch
    ):
        """Test user cannot update other's booking"""
        booking_id = populate_bookings[2].booking_id  # User 2's booking
        update_data = {"start_time": "09:00:00"}
        
        response = client.put(
            f"/api/bookings/{booking_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.integration
    def test_update_cancelled_booking_fails(
        self, client, test_db, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test updating cancelled booking fails"""
        booking_id = populate_bookings[0].booking_id
        
        # Cancel the booking
        booking = test_db.query(type(populate_bookings[0])).filter_by(
            booking_id=booking_id
        ).first()
        booking.status = "cancelled"
        test_db.commit()
        
        update_data = {"start_time": "09:00:00"}
        response = client.put(
            f"/api/bookings/{booking_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestCancelBooking:
    """Test DELETE /api/bookings/{booking_id} endpoint"""
    
    @pytest.mark.integration
    def test_cancel_booking_success(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test successful booking cancellation"""
        booking_id = populate_bookings[0].booking_id
        
        response = client.delete(f"/api/bookings/{booking_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["booking_id"] == booking_id
        assert "cancelled_at" in data
    
    @pytest.mark.integration
    def test_cancel_booking_not_found(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test cancelling non-existent booking fails"""
        response = client.delete("/api/bookings/999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.integration
    def test_cancel_booking_not_owner(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test user cannot cancel other's booking"""
        booking_id = populate_bookings[2].booking_id  # User 2's booking
        
        response = client.delete(f"/api/bookings/{booking_id}")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.integration
    def test_cancel_already_cancelled_booking(
        self, client, test_db, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test cancelling already-cancelled booking fails"""
        booking_id = populate_bookings[0].booking_id
        
        # Cancel first time
        response1 = client.delete(f"/api/bookings/{booking_id}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Try to cancel again
        response2 = client.delete(f"/api/bookings/{booking_id}")
        
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.integration
    def test_cancel_booking_soft_delete(
        self, client, test_db, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test booking is soft-deleted (record preserved)"""
        booking_id = populate_bookings[0].booking_id
        
        response = client.delete(f"/api/bookings/{booking_id}")
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify record still exists in database with cancelled status
        from models import Booking
        booking = test_db.query(Booking).filter(
            Booking.booking_id == booking_id
        ).first()
        
        assert booking is not None
        assert booking.status == "cancelled"


class TestCheckAvailability:
    """Test GET /api/bookings/availability/check endpoint"""
    
    @pytest.mark.integration
    def test_check_availability_available(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test availability check for available time slot"""
        tomorrow = date.today() + timedelta(days=10)
        
        response = client.get(
            "/api/bookings/availability/check",
            params={
                "room_id": 1,
                "booking_date": str(tomorrow),
                "start_time": "09:00:00",
                "end_time": "10:00:00"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available"] is True
        assert "Available" in data["message"]
    
    @pytest.mark.integration
    def test_check_availability_not_available(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test availability check for booked time slot"""
        tomorrow = date.today() + timedelta(days=1)
        
        response = client.get(
            "/api/bookings/availability/check",
            params={
                "room_id": 1,
                "booking_date": str(tomorrow),
                "start_time": "09:30:00",
                "end_time": "10:30:00"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available"] is False
        assert "already booked" in data["message"].lower()
    
    @pytest.mark.integration
    def test_check_availability_invalid_time_format(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test availability check with invalid time format"""
        tomorrow = date.today() + timedelta(days=1)
        
        response = client.get(
            "/api/bookings/availability/check",
            params={
                "room_id": 1,
                "booking_date": str(tomorrow),
                "start_time": "invalid",
                "end_time": "10:00:00"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestGetRoomSchedule:
    """Test GET /api/bookings/room/{room_id}/schedule endpoint"""
    
    @pytest.mark.integration
    def test_get_room_schedule(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test retrieving room schedule"""
        tomorrow = date.today() + timedelta(days=1)
        
        response = client.get(
            f"/api/bookings/room/1/schedule",
            params={"date": str(tomorrow)}
        )
        
        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        assert len(bookings) == 2
        assert all(b["room_id"] == 1 for b in bookings)
    
    @pytest.mark.integration
    def test_get_room_schedule_empty(
        self, client, populate_sample_room,
        mock_get_current_user_regular
    ):
        """Test room schedule for empty date"""
        future = date.today() + timedelta(days=100)
        
        response = client.get(
            f"/api/bookings/room/1/schedule",
            params={"date": str(future)}
        )
        
        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        assert len(bookings) == 0


class TestGetBookingHistory:
    """Test GET /api/bookings/{booking_id}/history endpoint"""
    
    @pytest.mark.integration
    def test_get_booking_history(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test retrieving booking history"""
        booking_id = populate_bookings[0].booking_id
        
        response = client.get(f"/api/bookings/{booking_id}/history")
        
        # Might have no history if no history records created, but endpoint should work
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.integration
    def test_get_booking_history_not_owner(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test user cannot view history of other's booking"""
        booking_id = populate_bookings[2].booking_id  # User 2's booking
        
        response = client.get(f"/api/bookings/{booking_id}/history")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetUserBookingHistory:
    """Test GET /api/bookings/user/{user_id}/history endpoint"""
    
    @pytest.mark.integration
    def test_get_user_booking_history(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test retrieving user's booking history"""
        response = client.get("/api/bookings/user/1/history")
        
        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        assert len(bookings) == 2
    
    @pytest.mark.integration
    def test_get_user_booking_history_forbidden(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test user cannot view other user's history"""
        response = client.get("/api/bookings/user/2/history")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.integration
    def test_get_user_booking_history_admin(
        self, client, populate_bookings,
        mock_get_current_user_admin
    ):
        """Test admin can view any user's history"""
        response = client.get("/api/bookings/user/1/history")
        
        assert response.status_code == status.HTTP_200_OK


class TestAccessControl:
    """Test role-based access control"""
    
    @pytest.mark.integration
    def test_regular_user_sees_own_bookings_only(
        self, client, populate_bookings,
        mock_get_current_user_regular
    ):
        """Test regular user sees only their bookings in list"""
        response = client.get("/api/bookings/")
        
        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        assert all(b["user_id"] == 1 for b in bookings)
        assert len(bookings) == 2
    
    @pytest.mark.integration
    def test_facility_manager_sees_all_bookings(
        self, client, populate_bookings,
        mock_get_current_user_manager
    ):
        """Test facility manager sees all bookings"""
        response = client.get("/api/bookings/")
        
        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        assert len(bookings) >= 3
