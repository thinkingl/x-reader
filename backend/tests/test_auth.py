import pytest
import hashlib
import hmac
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, init_db
from app.models.database import Base, SystemConfig
from app.services.auth import (
    generate_salt,
    hash_key,
    generate_nonce,
    generate_timestamp,
    verify_timestamp,
    compute_hmac_response,
    verify_hmac_response,
    create_jwt_token,
    verify_jwt_token,
    AuthManager,
)

# Use fixtures from conftest.py
# client fixture is defined in conftest.py


@pytest.fixture
def db():
    # Use the same engine as conftest.py
    from tests.conftest import engine, TestingSessionLocal
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


# Unit tests for auth functions
class TestAuthFunctions:
    def test_generate_salt(self):
        salt = generate_salt()
        assert len(salt) == 32
        assert all(c in "0123456789abcdef" for c in salt)

    def test_hash_key(self):
        salt = "testsalt"
        key = "testkey"
        result = hash_key(salt, key)
        expected = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()
        assert result == expected

    def test_generate_nonce(self):
        nonce = generate_nonce()
        assert len(nonce) == 32
        assert all(c in "0123456789abcdef" for c in nonce)

    def test_generate_timestamp(self):
        ts = generate_timestamp()
        assert abs(ts - time.time()) < 2

    def test_verify_timestamp_valid(self):
        ts = int(time.time())
        assert verify_timestamp(ts) is True

    def test_verify_timestamp_expired(self):
        ts = int(time.time()) - 120
        assert verify_timestamp(ts) is False

    def test_compute_hmac_response(self):
        key = "testkey"
        nonce = "testnonce"
        timestamp = 1234567890
        result = compute_hmac_response(key, nonce, timestamp)
        expected = hmac.new(
            key.encode(),
            f"{nonce}{timestamp}".encode(),
            hashlib.sha256,
        ).hexdigest()
        assert result == expected

    def test_verify_hmac_response(self):
        key = "testkey"
        nonce = "testnonce"
        timestamp = 1234567890
        response = compute_hmac_response(key, nonce, timestamp)
        assert verify_hmac_response(key, nonce, timestamp, response) is True
        assert verify_hmac_response(key, nonce, timestamp, "wrong") is False

    def test_create_jwt_token(self):
        token = create_jwt_token("testhash")
        assert token is not None
        assert isinstance(token, str)

    def test_verify_jwt_token_valid(self):
        token = create_jwt_token("testhash")
        assert verify_jwt_token(token) is True

    def test_verify_jwt_token_invalid(self):
        assert verify_jwt_token("invalid.token.here") is False


# Integration tests for auth API
class TestAuthAPI:
    def test_get_auth_status_disabled(self, client):
        response = client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["has_key"] is False

    def test_get_auth_challenge(self, client):
        response = client.post("/api/auth/challenge")
        assert response.status_code == 200
        data = response.json()
        assert "nonce" in data
        assert "timestamp" in data
        assert "salt" in data

    def test_enable_auth(self, client):
        salt = "testsalt12345678"
        key = "mysecretkey"
        key_hash = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()

        response = client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify auth is now enabled
        status_response = client.get("/api/auth/status")
        assert status_response.json()["enabled"] is True

    def test_enable_auth_already_enabled(self, client, db):
        # First enable auth
        salt = "testsalt12345678"
        key = "mysecretkey"
        key_hash = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()

        client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )

        # Try to enable again
        response = client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )
        assert response.json()["success"] is False
        assert "已启用" in response.json()["message"]

    def test_auth_required_for_protected_route(self, client, db):
        # Enable auth
        salt = "testsalt12345678"
        key = "mysecretkey"
        key_hash = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()

        client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )

        # Try to access protected route without token
        response = client.get("/api/books")
        assert response.status_code == 401

    def test_auth_with_valid_token(self, client, db):
        # Enable auth
        salt = "testsalt12345678"
        key = "mysecretkey"
        key_hash = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()

        client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )

        # Login to get token
        challenge_response = client.post("/api/auth/challenge")
        challenge_data = challenge_response.json()

        nonce = challenge_data["nonce"]
        timestamp = challenge_data["timestamp"]

        # Use the key_hash (stored hash) for HMAC
        response_str = hmac.new(
            key_hash.encode(),
            f"{nonce}{timestamp}".encode(),
            hashlib.sha256,
        ).hexdigest()

        verify_response = client.post(
            "/api/auth/verify",
            json={"response": response_str, "timestamp": timestamp},
        )
        assert verify_response.status_code == 200
        token = verify_response.json()["token"]

        # Access protected route with token
        response = client.get(
            "/api/books",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_auth_with_invalid_token(self, client, db):
        # Enable auth
        salt = "testsalt12345678"
        key = "mysecretkey"
        key_hash = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()

        client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )

        # Try with invalid token
        response = client.get(
            "/api/books",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_disable_auth(self, client, db):
        # Enable auth
        salt = "testsalt12345678"
        key = "mysecretkey"
        key_hash = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()

        client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )

        # Login to get token
        challenge_response = client.post("/api/auth/challenge")
        challenge_data = challenge_response.json()

        nonce = challenge_data["nonce"]
        timestamp = challenge_data["timestamp"]

        # Use key_hash for HMAC
        response_str = hmac.new(
            key_hash.encode(),
            f"{nonce}{timestamp}".encode(),
            hashlib.sha256,
        ).hexdigest()

        verify_response = client.post(
            "/api/auth/verify",
            json={"response": response_str, "timestamp": timestamp},
        )
        token = verify_response.json()["token"]

        # Disable auth
        disable_challenge = client.post("/api/auth/challenge")
        disable_challenge_data = disable_challenge.json()

        disable_nonce = disable_challenge_data["nonce"]
        disable_timestamp = disable_challenge_data["timestamp"]

        disable_response_str = hmac.new(
            key_hash.encode(),
            f"{disable_nonce}{disable_timestamp}".encode(),
            hashlib.sha256,
        ).hexdigest()

        disable_response = client.post(
            "/api/auth/disable",
            json={"response": disable_response_str, "timestamp": disable_timestamp},
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["success"] is True

        # Verify auth is now disabled
        status_response = client.get("/api/auth/status")
        assert status_response.json()["enabled"] is False

    def test_disable_auth_with_wrong_key(self, client, db):
        # Enable auth
        salt = "testsalt12345678"
        key = "mysecretkey"
        key_hash = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()

        client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )

        # Try to disable with wrong key
        challenge_response = client.post("/api/auth/challenge")
        challenge_data = challenge_response.json()

        nonce = challenge_data["nonce"]
        timestamp = challenge_data["timestamp"]

        wrong_key = "wrongkey"
        response_str = hmac.new(
            wrong_key.encode(),
            f"{nonce}{timestamp}".encode(),
            hashlib.sha256,
        ).hexdigest()

        disable_response = client.post(
            "/api/auth/disable",
            json={"response": response_str, "timestamp": timestamp},
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["success"] is False

    def test_auth_disabled_allows_access(self, client, db):
        # Auth is disabled by default
        response = client.get("/api/books")
        assert response.status_code == 200

    def test_get_config_no_auth_required(self, client, db):
        # Enable auth
        salt = "testsalt12345678"
        key = "mysecretkey"
        key_hash = hashlib.sha256(f"{salt}{key}".encode()).hexdigest()

        client.post(
            "/api/auth/enable",
            json={"key_hash": key_hash, "key_salt": salt},
        )

        # GET /api/config should not require auth
        response = client.get("/api/config")
        assert response.status_code == 200


# AuthManager tests
class TestAuthManager:
    def test_is_auth_enabled_default(self, db):
        am = AuthManager(db)
        assert am.is_auth_enabled() is False

    def test_enable_auth(self, db):
        am = AuthManager(db)
        result = am.enable_auth("testhash", "testsalt")
        assert result["success"] is True
        assert am.is_auth_enabled() is True

    def test_get_auth_status(self, db):
        am = AuthManager(db)
        status = am.get_auth_status()
        assert status["enabled"] is False
        assert status["has_key"] is False

        am.enable_auth("testhash", "testsalt")
        status = am.get_auth_status()
        assert status["enabled"] is True
        assert status["has_key"] is True

    def test_create_challenge(self, db):
        am = AuthManager(db)
        challenge = am.create_challenge()
        assert "nonce" in challenge
        assert "timestamp" in challenge
        assert "salt" in challenge

    def test_cleanup_expired_challenges(self, db):
        am = AuthManager(db)
        am.create_challenge()
        am.cleanup_expired_challenges()
