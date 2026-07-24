"""
Tests verifying the authentication backend server endpoints.
"""
from fastapi.testclient import TestClient
import pytest
from backend.main import app
from database.connection import initialize_database

# Initialize database schema and perform migrations
initialize_database()

client = TestClient(app)


def test_auth_me_unauthorized():
    """Verify that accessing /auth/me returns the bypassed developer user directly."""
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json().get("email") == "developer@mediverse.ai"



def test_invalid_login():
    """Verify that logging in with invalid credentials returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "nonexistent@mediverse.ai", "password": "wrongpassword123"}
    )
    assert response.status_code == 401


def test_password_strength_validation():
    """Verify that registering with a weak password fails validation."""
    response = client.post(
        "/auth/register",
        json={
            "email": "testuser@mediverse.ai",
            "username": "testuser",
            "password": "123",  # Weak password
            "full_name": "Test User"
        }
    )
    assert response.status_code == 400
    assert "must be at least" in response.json().get("detail", "").lower()
