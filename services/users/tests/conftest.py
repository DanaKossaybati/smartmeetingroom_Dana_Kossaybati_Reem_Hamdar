import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from database import Base, get_db
from models import User

# Use in-memory SQLite for fast, isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create engine at module level
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=None
)

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh in-memory database for each test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Don't drop tables - just clear data
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_user_data():
    """Sample user data for registration tests"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "role": "regular_user"
    }

@pytest.fixture
def sample_admin_data():
    """Sample admin user data"""
    return {
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "full_name": "Admin User",
        "role": "admin"
    }

@pytest.fixture
def create_test_user(client, sample_user_data):
    """Create a test user and return user data with token"""
    # Register user
    response = client.post("/api/users/register", json=sample_user_data)
    assert response.status_code == 201
    user_data = response.json()
    
    # Login to get token - USING JSON FORMAT (THIS IS THE KEY FIX!)
    login_response = client.post(
        "/api/users/login",
        json={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Create a simple user object to return
    class UserObj:
        def __init__(self, data):
            self.username = data.get("username")
            self.email = data.get("email")
            self.user_id = data.get("user_id")
            self.role = data.get("role", "regular_user")
    
    return UserObj(user_data), token

@pytest.fixture
def create_test_admin(client, sample_admin_data):
    """Create an admin user and return admin data with token"""
    # Register admin
    response = client.post("/api/users/register", json=sample_admin_data)
    assert response.status_code == 201
    admin_data = response.json()
    
    # Login to get token - USING JSON FORMAT
    login_response = client.post(
        "/api/users/login",
        json={
            "username": sample_admin_data["username"],
            "password": sample_admin_data["password"]
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Create a simple admin object to return
    class UserObj:
        def __init__(self, data):
            self.username = data.get("username")
            self.email = data.get("email")
            self.user_id = data.get("user_id")
            self.role = data.get("role", "admin")
    
    return UserObj(admin_data), token

@pytest.fixture
def auth_headers(create_test_user):
    """Get authentication headers for regular user"""
    _, token = create_test_user
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(create_test_admin):
    """Get authentication headers for admin user"""
    _, token = create_test_admin
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def sample_update_data():
    """Sample data for profile updates"""
    return {
        "email": "newemail@example.com",
        "full_name": "Updated Name"
    }

@pytest.fixture
def second_user_data():
    """Data for creating a second test user"""
    return {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "SecurePass456!",
        "full_name": "Test User Two"
    }

@pytest.fixture
def facility_manager_data():
    """Data for creating a facility manager user"""
    return {
        "username": "facilitymanager",
        "email": "fm@example.com",
        "password": "FMPass123!",
        "full_name": "Facility Manager",
        "role": "facility_manager"
    }

@pytest.fixture
def moderator_data():
    """Data for creating a moderator user"""
    return {
        "username": "moderator",
        "email": "mod@example.com",
        "password": "ModPass123!",
        "full_name": "Moderator User",
        "role": "moderator"
    }

@pytest.fixture
def auditor_data():
    """Data for creating an auditor user"""
    return {
        "username": "auditor",
        "email": "auditor@example.com",
        "password": "AuditPass123!",
        "full_name": "Auditor User",
        "role": "auditor"
    }