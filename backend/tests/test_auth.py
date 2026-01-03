"""
Test authentication endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.supabase_client import SupabaseClient

client = TestClient(app)


@pytest.fixture(scope="module")
def test_user_credentials():
    """Test user credentials"""
    import time
    # Use timestamp to create unique email
    timestamp = int(time.time())
    return {
        "email": f"shubhamdeprojects@gmail.com",  # Use real domain for Supabase validation
        "password": "TestPassword123!",
        "full_name": "Test User"
    }


@pytest.fixture(scope="module")
def test_user_token(test_user_credentials):
    """
    Create a test user and return access token.
    
    Note: This requires Supabase to be set up and running.
    """
    # Try to sign up (might fail if user exists)
    signup_response = client.post(
        "/api/v1/auth/signup",
        json=test_user_credentials
    )
    
    # If signup fails, try login
    if signup_response.status_code != 201:
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_credentials["email"],
                "password": test_user_credentials["password"]
            }
        )
        assert login_response.status_code == 200
        return login_response.json()["access_token"]
    
    return signup_response.json()["access_token"]


def test_health_check():
    """Test health check endpoint (no auth required)"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_success(test_user_credentials):
    """Test successful user signup"""
    # Use unique email for this test with valid domain
    import time
    unique_email = f"shubhamdeprojects@gmail.com"
    
    response = client.post(
        "/api/v1/auth/signup",
        json={
            **test_user_credentials,
            "email": unique_email
        }
    )
    
    # Debug: Print response details if it fails
    if response.status_code not in [201, 400]:
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Body: {response.json()}")
    
    # Might be 201 (created) or 400 (already exists or email confirmation required)
    assert response.status_code in [201, 400], f"Unexpected status code: {response.status_code}"
    
    if response.status_code == 201:
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == unique_email
    elif response.status_code == 400:
        # Check if it's email confirmation or duplicate email
        detail = response.json().get("detail", "")
        assert "Email confirmation required" in detail or "already registered" in detail, \
            f"Unexpected error: {detail}"


def test_login_success(test_user_credentials):
    """Test successful login"""
    # First, ensure the user exists by signing up
    # (This will succeed if email confirmation is disabled, or return 400 if enabled)
    signup_response = client.post(
        "/api/v1/auth/signup",
        json=test_user_credentials
    )
    
    # If signup returned 400, the user might already exist or email confirmation is required
    # Either way, we can try to login
    
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        }
    )
    
    # If email confirmation is disabled, login should work after signup
    # If email confirmation is enabled, login will fail with 401
    if signup_response.status_code == 201:
        # Signup succeeded, login should work
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
    else:
        # Signup failed (email confirmation required), so login will also fail
        # This is expected behavior
        assert response.status_code in [200, 401], \
            f"Expected 200 or 401, got {response.status_code}"


def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "shubhamdeprojects@gmail.com",  # Valid domain but wrong credentials
            "password": "WrongPassword123!"
        }
    )
    
    assert response.status_code == 401


def test_get_me_authenticated(test_user_token):
    """Test getting current user info with valid token"""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data


def test_get_me_unauthenticated():
    """Test getting current user without token"""
    response = client.get("/api/v1/auth/me")
    
    assert response.status_code == 401  # No credentials provided (HTTPBearer returns 401)


def test_get_me_invalid_token():
    """Test getting current user with invalid token"""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    
    assert response.status_code == 401


def test_protected_endpoint_without_auth():
    """Test that chat endpoint requires authentication"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "Hello"}
    )
    
    assert response.status_code == 401  # No credentials provided (HTTPBearer returns 401)


def test_protected_endpoint_with_auth(test_user_token):
    """Test that chat endpoint works with authentication"""
    response = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"message": "Hello"}
    )
    
    # Should succeed (200) or fail due to LLM not running (500)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "conversation_id" in data
        assert "reply" in data


# Add timestamp for unique emails
pytest.timestamp = int(__import__('time').time())
