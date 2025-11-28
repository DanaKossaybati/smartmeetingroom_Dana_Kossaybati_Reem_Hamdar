"""
Pytest configuration and fixtures for Bookings Service tests.
Provides database setup, client configuration, and test data fixtures.

Author: Testing Suite
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
from datetime import date, time, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from database import Base, get_db
from models import Booking, BookingHistory, Room
import auth

# Use file-based SQLite for testing (more reliable than in-memory for multiple sessions)
import tempfile
TEST_DATABASE_URL = f"sqlite:///{tempfile.gettempdir()}/test_bookings.db"

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Drop all tables and recreate them for a fresh database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database and auth override"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    # Override get_db dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Only clear non-auth dependencies from client itself
    # Auth mocks will manage their own cleanup
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]

# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_booking_data():
    """Sample booking data for creating test bookings"""
    tomorrow = date.today() + timedelta(days=1)
    return {
        "room_id": 1,
        "booking_date": tomorrow.isoformat(),
        "start_time": "14:00:00",
        "end_time": "15:30:00",
        "purpose": "Team meeting"
    }

@pytest.fixture
def sample_booking_data_morning():
    """Sample booking data for morning time slot"""
    tomorrow = date.today() + timedelta(days=1)
    return {
        "room_id": 1,
        "booking_date": tomorrow.isoformat(),
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "purpose": "Morning standup"
    }

@pytest.fixture
def sample_booking_data_afternoon():
    """Sample booking data for afternoon time slot"""
    tomorrow = date.today() + timedelta(days=1)
    return {
        "room_id": 1,
        "booking_date": tomorrow.isoformat(),
        "start_time": "15:00:00",
        "end_time": "16:00:00",
        "purpose": "Afternoon sync"
    }

@pytest.fixture
def sample_user_data():
    """Sample user data for authentication tests"""
    return {
        "user_id": 1,
        "username": "testuser",
        "role": "regular_user"
    }

@pytest.fixture
def sample_admin_data():
    """Sample admin user data"""
    return {
        "user_id": 999,
        "username": "adminuser",
        "role": "admin"
    }

@pytest.fixture
def sample_manager_data():
    """Sample facility manager user data"""
    return {
        "user_id": 888,
        "username": "manageruser",
        "role": "facility_manager"
    }

@pytest.fixture
def sample_room():
    """Create a sample room in the database"""
    room = Room(
        room_id=1,
        room_name="Conference Room A",
        capacity=10,
        location="Building 1, Floor 2",
        description="Meeting room with projector and whiteboard",
        status="available"
    )
    return room

# ============================================================================
# Database Population Fixtures
# ============================================================================

@pytest.fixture
def populate_sample_room(test_db, sample_room):
    """Create a sample room in database"""
    test_db.add(sample_room)
    test_db.commit()
    return sample_room

@pytest.fixture
def populate_bookings(test_db, populate_sample_room):
    """Create multiple sample bookings for testing"""
    tomorrow = date.today() + timedelta(days=1)
    
    bookings = [
        Booking(
            user_id=1,
            room_id=1,
            booking_date=tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="confirmed",
            purpose="Morning standup"
        ),
        Booking(
            user_id=1,
            room_id=1,
            booking_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(15, 30),
            status="confirmed",
            purpose="Team meeting"
        ),
        Booking(
            user_id=2,
            room_id=1,
            booking_date=tomorrow + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="confirmed",
            purpose="One-on-one"
        ),
    ]
    
    for booking in bookings:
        test_db.add(booking)
    test_db.commit()
    
    return bookings

# ============================================================================
# Authentication Fixtures for Mocking JWT
# ============================================================================

@pytest.fixture
def auth_headers_user(sample_user_data):
    """Get mock authentication headers for regular user (without actually logging in)"""
    # This is a mock - in real test, would need to mock the JWT verification
    return {
        "Authorization": "Bearer mock_token_user"
    }

@pytest.fixture
def auth_headers_admin(sample_admin_data):
    """Get mock authentication headers for admin user"""
    return {
        "Authorization": "Bearer mock_token_admin"
    }

@pytest.fixture
def auth_headers_manager(sample_manager_data):
    """Get mock authentication headers for facility manager"""
    return {
        "Authorization": "Bearer mock_token_manager"
    }

# ============================================================================
# Mock/Patch Fixtures for External Service Calls
# ============================================================================

@pytest.fixture
def mock_get_current_user_regular(sample_user_data):
    """Mock get_current_user to return regular user"""
    def mock_user():
        return sample_user_data
    
    # Override the dependency in FastAPI
    app.dependency_overrides[auth.get_current_user] = mock_user
    yield sample_user_data
    # Clean up auth override
    if auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]

@pytest.fixture
def mock_get_current_user_admin(sample_admin_data):
    """Mock get_current_user to return admin user"""
    def mock_user():
        return sample_admin_data
    
    # Override the dependency in FastAPI
    app.dependency_overrides[auth.get_current_user] = mock_user
    yield sample_admin_data
    # Clean up auth override
    if auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]

@pytest.fixture
def mock_get_current_user_manager(sample_manager_data):
    """Mock get_current_user to return facility manager user"""
    def mock_user():
        return sample_manager_data
    
    # Override the dependency in FastAPI
    app.dependency_overrides[auth.get_current_user] = mock_user
    yield sample_manager_data
    # Clean up auth override
    if auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]

# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as a smoke test for critical functionality"
    )
    config.addinivalue_line(
        "markers", "edge_case: mark test as testing edge cases"
    )
