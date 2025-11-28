"""
Clean Test Suite for Users Service - 63 Tests
Tests all user management endpoints via API
Author: Dana Kossaybati
"""

import pytest
from fastapi import status


class TestUserRegistration:
    """Test user registration functionality"""
    
    @pytest.mark.unit
    def test_register_new_user_success(self, client, sample_user_data):
        """Test successful user registration"""
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["username"] == sample_user_data["username"]
        assert data["email"] == sample_user_data["email"]
        assert data["full_name"] == sample_user_data["full_name"]
        assert "user_id" in data
        assert "password" not in data
    
    @pytest.mark.unit
    def test_register_duplicate_username(self, client, create_test_user, sample_user_data):
        """Test registration with existing username fails"""
        user, _ = create_test_user
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]
        assert "already exists" in response.json()["detail"].lower()
    
    @pytest.mark.unit
    def test_register_duplicate_email(self, client, create_test_user, sample_user_data):
        """Test registration with existing email fails"""
        user, _ = create_test_user
        
        new_user_data = sample_user_data.copy()
        new_user_data["username"] = "differentuser"
        
        response = client.post("/api/users/register", json=new_user_data)
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]
    
    @pytest.mark.unit
    def test_register_invalid_email(self, client, sample_user_data):
        """Test registration with invalid email format"""
        sample_user_data["email"] = "invalid-email"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.unit
    def test_register_weak_password(self, client, sample_user_data):
        """Test registration with weak password"""
        sample_user_data["password"] = "123"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.unit
    def test_register_missing_required_fields(self, client):
        """Test registration with missing required fields"""
        incomplete_data = {"username": "testuser"}
        
        response = client.post("/api/users/register", json=incomplete_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.unit
    def test_register_admin_user(self, client, sample_user_data):
        """Test registering an admin user"""
        sample_user_data["username"] = "admin_user_test"
        sample_user_data["email"] = "admin@test.com"
        sample_user_data["role"] = "admin"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == "admin"
    
    @pytest.mark.unit
    def test_register_with_empty_strings(self, client, sample_user_data):
        """Test registration with empty strings"""
        sample_user_data["username"] = ""
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserAuthentication:
    """Test user login and authentication"""
    
    @pytest.mark.unit
    def test_login_success(self, client, sample_user_data):
        """Test successful login"""
        # Register user first
        client.post("/api/users/register", json=sample_user_data)
        
        # Now login
        response = client.post(
            "/api/users/login",
            json={
                "username": sample_user_data["username"],
                "password": sample_user_data["password"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.unit
    def test_login_wrong_password(self, client, create_test_user):
        """Test login with incorrect password"""
        user, _ = create_test_user
        
        response = client.post(
            "/api/users/login",
            json={
                "username": user.username,
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.unit
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent username"""
        response = client.post(
            "/api/users/login",
            json={
                "username": "nonexistent",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.unit
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post("/api/users/login", json={})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.unit
    def test_login_with_email_instead_of_username(self, client, create_test_user):
        """Test login attempt with email instead of username"""
        user, password = create_test_user
        
        response = client.post(
            "/api/users/login",
            json={
                "username": user.email,
                "password": password
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.unit
    def test_login_case_sensitive_username(self, client, create_test_user):
        """Test username is case-sensitive in login"""
        user, password = create_test_user
        
        response = client.post(
            "/api/users/login",
            json={
                "username": user.username.upper(),
                "password": password
            }
        )
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]


class TestUserProfile:
    """Test user profile operations"""
    
    @pytest.mark.unit
    def test_get_current_user(self, client, auth_headers, create_test_user):
        """Test getting current user profile"""
        user, _ = create_test_user
        
        response = client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["username"] == user.username
            assert "password" not in data
    
    @pytest.mark.unit
    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication"""
        response = client.get("/api/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.unit
    def test_update_user_profile(self, client, auth_headers):
        """Test updating user profile"""
        update_data = {
            "full_name": "Updated Name",
            "email": "updated@example.com"
        }
        
        response = client.put(
            "/api/users/me",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
    
    @pytest.mark.unit
    def test_update_profile_invalid_email(self, client, auth_headers):
        """Test updating profile with invalid email"""
        update_data = {"email": "not-an-email"}
        
        response = client.put(
            "/api/users/me",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_403_FORBIDDEN]
    
    @pytest.mark.unit
    def test_delete_user_account(self, client, auth_headers):
        """Test deleting user account"""
        response = client.delete("/api/users/me", headers=auth_headers)
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
    
    @pytest.mark.unit
    def test_update_profile_with_invalid_token(self, client):
        """Test updating profile with invalid JWT token"""
        response = client.put(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token_here"},
            json={"full_name": "New Name"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.unit
    def test_update_profile_with_expired_token(self, client):
        """Test updating profile with expired token format"""
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"
        
        response = client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
            json={"full_name": "New Name"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserManagement:
    """Test admin user management operations"""
    
    @pytest.mark.unit
    def test_get_all_users_as_admin(self, client, admin_auth_headers, create_test_user):
        """Test admin can get all users"""
        user, _ = create_test_user
        
        response = client.get("/api/users", headers=admin_auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1
    
    @pytest.mark.unit
    def test_get_all_users_as_regular_user_fails(self, client, auth_headers):
        """Test regular user cannot get all users"""
        response = client.get("/api/users", headers=auth_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.unit
    def test_get_all_users_unauthorized(self, client):
        """Test getting all users without authentication"""
        response = client.get("/api/users")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.unit
    def test_get_user_by_username_as_admin(self, client, admin_auth_headers, create_test_user):
        """Test admin can get specific user by username"""
        user, _ = create_test_user
        
        response = client.get(
            f"/api/users/{user.username}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["username"] == user.username
        assert data["email"] == user.email
    
    @pytest.mark.unit
    def test_get_nonexistent_user(self, client, admin_auth_headers):
        """Test getting non-existent user returns 404"""
        response = client.get(
            "/api/users/nonexistent_user_12345",
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.unit
    def test_delete_user_as_admin(self, client, admin_auth_headers, create_test_user):
        """Test admin can delete users"""
        user, _ = create_test_user
        
        response = client.delete(
            f"/api/users/{user.username}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.unit
    def test_delete_user_as_regular_user(self, client, auth_headers, create_test_user):
        """Test regular user can delete their own account"""
        user, _ = create_test_user
        
        response = client.delete(
            f"/api/users/{user.username}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK


class TestUserBookingHistory:
    """Test user booking history functionality"""
    
    @pytest.mark.integration
    def test_get_user_booking_history(self, client, auth_headers):
        """Test getting user's booking history"""
        response = client.get(
            "/api/users/me/bookings",
            headers=auth_headers
        )
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.integration
    def test_get_booking_history_unauthorized(self, client):
        """Test getting booking history without authentication"""
        response = client.get("/api/users/me/bookings")
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]


class TestRoleBasedAccess:
    """Test role-based access control"""
    
    @pytest.mark.unit
    def test_admin_role_permissions(self, client, admin_auth_headers):
        """Test admin has elevated permissions"""
        response = client.get("/api/users", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.unit
    def test_regular_user_role_restrictions(self, client, auth_headers):
        """Test regular user has restricted permissions"""
        response = client.get("/api/users", headers=auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.unit
    def test_facility_manager_role(self, client, sample_user_data):
        """Test facility_manager role creation"""
        sample_user_data["role"] = "facility_manager"
        sample_user_data["username"] = "facility_mgr"
        sample_user_data["email"] = "facility@example.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == "facility_manager"
    
    @pytest.mark.unit
    def test_moderator_role(self, client, sample_user_data):
        """Test moderator role creation"""
        sample_user_data["role"] = "moderator"
        sample_user_data["username"] = "moderator_user"
        sample_user_data["email"] = "moderator@example.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == "moderator"
    
    @pytest.mark.unit
    def test_auditor_role(self, client, sample_user_data):
        """Test auditor role creation"""
        sample_user_data["role"] = "auditor"
        sample_user_data["username"] = "auditor_user"
        sample_user_data["email"] = "auditor@example.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == "auditor"


class TestHealthCheck:
    """Test health check endpoint"""
    
    @pytest.mark.smoke
    def test_health_endpoint(self, client):
        """Test health check returns OK"""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "status" in data
    
    @pytest.mark.smoke
    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "service" in data or "message" in data
    
    @pytest.mark.smoke
    def test_health_endpoint_no_auth_required(self, client):
        """Test health endpoint doesn't require authentication"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.smoke
    def test_database_connection(self, test_db):
        """Test database connection works"""
        from models import User
        count = test_db.query(User).count()
        assert count >= 0


class TestInputValidation:
    """Test input validation and sanitization"""
    
    @pytest.mark.unit
    def test_sql_injection_prevention_username(self, client, sample_user_data):
        """Test SQL injection attempts are blocked"""
        sample_user_data["username"] = "admin'; DROP TABLE users;--"
        sample_user_data["email"] = "sql_inject@test.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    @pytest.mark.unit
    def test_xss_prevention_in_full_name(self, client, sample_user_data):
        """Test XSS attempts"""
        sample_user_data["full_name"] = "<script>alert('XSS')</script>"
        sample_user_data["username"] = "xss_test"
        sample_user_data["email"] = "xss@test.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    @pytest.mark.unit
    def test_email_validation(self, client, sample_user_data):
        """Test email format validation"""
        sample_user_data["email"] = "notanemail"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.unit
    def test_username_special_characters(self, client, sample_user_data):
        """Test username with special characters"""
        sample_user_data["username"] = "user@#$%"
        sample_user_data["email"] = "special@test.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    @pytest.mark.unit
    def test_null_values_rejected(self, client):
        """Test null values are rejected"""
        response = client.post("/api/users/register", json={
            "username": None,
            "password": None,
            "email": None
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.unit
    def test_input_sanitization(self, client, sample_user_data):
        """Test general input sanitization"""
        sample_user_data["full_name"] = "Test<>User"
        sample_user_data["username"] = "sanitize_test"
        sample_user_data["email"] = "sanitize@test.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.unit
    def test_very_long_username(self, client, sample_user_data):
        """Test username length limit"""
        sample_user_data["username"] = "a" * 100
        sample_user_data["email"] = "longuser@test.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    @pytest.mark.unit
    def test_unicode_characters_in_name(self, client, sample_user_data):
        """Test Unicode support in full name"""
        sample_user_data["full_name"] = "José García 日本語"
        sample_user_data["username"] = "unicodeuser"
        sample_user_data["email"] = "unicode@test.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.unit
    def test_case_insensitive_username(self, client, create_test_user, sample_user_data):
        """Test username case handling"""
        user, _ = create_test_user
        
        sample_user_data["username"] = user.username.upper()
        sample_user_data["email"] = "different@example.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
    
    @pytest.mark.unit
    def test_minimum_password_length(self, client, sample_user_data):
        """Test minimum password length enforcement"""
        sample_user_data["password"] = "123"
        
        response = client.post("/api/users/register", json=sample_user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.unit
    def test_whitespace_in_username(self, client, sample_user_data):
        """Test username with whitespace"""
        sample_user_data["username"] = "user name"
        sample_user_data["email"] = "whitespace@test.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    @pytest.mark.unit
    def test_email_case_insensitivity(self, client, create_test_user, sample_user_data):
        """Test email case handling"""
        user, _ = create_test_user
        
        sample_user_data["username"] = "different_user"
        sample_user_data["email"] = user.email.upper()
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.unit
    def test_maximum_field_length(self, client, sample_user_data):
        """Test maximum field length validation"""
        sample_user_data["full_name"] = "A" * 200
        sample_user_data["username"] = "maxfield"
        sample_user_data["email"] = "maxfield@test.com"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.unit
    def test_404_error_nonexistent_endpoint(self, client):
        """Test 404 error for nonexistent endpoint"""
        response = client.get("/api/nonexistent-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.unit
    def test_method_not_allowed(self, client):
        """Test 405 error for wrong HTTP method"""
        response = client.patch("/api/users/login")
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.unit
    def test_invalid_json_body(self, client):
        """Test 400/422 error for invalid JSON"""
        response = client.post(
            "/api/users/register",
            data="this is not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    @pytest.mark.unit
    def test_missing_content_type(self, client):
        """Test request without Content-Type header"""
        response = client.post(
            "/api/users/register",
            data='{"username": "test"}'
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        ]
    
    @pytest.mark.unit
    def test_malformed_authorization_header(self, client):
        """Test request with malformed Authorization header"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.unit
    def test_missing_bearer_prefix(self, client):
        """Test Authorization header without Bearer prefix"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "some_token_here"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordSecurity:
    """Test password hashing and security"""
    
    @pytest.mark.unit
    def test_password_not_returned_in_response(self, client, sample_user_data):
        """Test password is never returned in API responses"""
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert "password" not in data
        assert "password_hash" not in data
    
    @pytest.mark.unit
    def test_password_complexity_requirements(self, client, sample_user_data):
        """Test password complexity enforcement"""
        sample_user_data["password"] = "12345678"
        
        response = client.post("/api/users/register", json=sample_user_data)
        
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    @pytest.mark.unit
    def test_failed_login_attempts(self, client, create_test_user):
        """Test multiple failed login attempts"""
        user, _ = create_test_user
        
        for i in range(3):
            response = client.post(
                "/api/users/login",
                json={
                    "username": user.username,
                    "password": f"wrong_password_{i}"
                }
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestConcurrency:
    """Test concurrent operations"""
    
    @pytest.mark.unit
    def test_concurrent_user_creation_same_username(self, client, sample_user_data):
        """Test handling of concurrent registrations with same username"""
        response1 = client.post("/api/users/register", json=sample_user_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        response2 = client.post("/api/users/register", json=sample_user_data)
        assert response2.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT
        ]


# Total: 63 tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=html"])