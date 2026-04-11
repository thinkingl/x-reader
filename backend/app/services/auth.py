import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import jwt
from sqlalchemy.orm import Session

from app.models.database import SystemConfig

JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60
CHALLENGE_EXPIRY_SECONDS = 60


def generate_salt() -> str:
    return secrets.token_hex(16)


def hash_key(salt: str, key: str) -> str:
    return hashlib.sha256(f"{salt}{key}".encode()).hexdigest()


def generate_nonce() -> str:
    return secrets.token_hex(16)


def generate_timestamp() -> int:
    return int(time.time())


def verify_timestamp(timestamp: int, max_age: int = CHALLENGE_EXPIRY_SECONDS) -> bool:
    return abs(time.time() - timestamp) <= max_age


def compute_hmac_response(key: str, nonce: str, timestamp: int) -> str:
    message = f"{nonce}{timestamp}"
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def verify_hmac_response(key: str, nonce: str, timestamp: int, response: str) -> bool:
    expected = compute_hmac_response(key, nonce, timestamp)
    return hmac.compare_digest(expected, response)


def create_jwt_token(key_hash: str) -> str:
    payload = {
        "sub": key_hash[:16],
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRY_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> bool:
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True
    except jwt.PyJWTError:
        return False


class AuthManager:
    def __init__(self, db: Session):
        self.db = db
        self._pending_challenges: dict[str, Tuple[str, int]] = {}

    def get_config(self, key: str) -> Optional[str]:
        config = self.db.query(SystemConfig).filter(SystemConfig.key == key).first()
        return config.value if config else None

    def set_config(self, key: str, value: str):
        config = self.db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            config.value = value
        else:
            self.db.add(SystemConfig(key=key, value=value))
        self.db.commit()

    def is_auth_enabled(self) -> bool:
        return self.get_config("auth_enabled") == "true"

    def get_auth_status(self) -> dict:
        return {
            "enabled": self.is_auth_enabled(),
            "has_key": self.get_config("auth_key_hash") is not None,
        }

    def enable_auth(self, key_hash: str, key_salt: str) -> dict:
        self.set_config("auth_enabled", "true")
        self.set_config("auth_key_hash", key_hash)
        self.set_config("auth_key_salt", key_salt)
        return {"success": True, "message": "认证已启用"}

    def disable_auth(self, response: str, timestamp: int) -> dict:
        if not self.is_auth_enabled():
            return {"success": False, "message": "认证未启用"}

        if not verify_timestamp(timestamp):
            return {"success": False, "message": "Challenge 已过期"}

        stored_hash = self.get_config("auth_key_hash")
        stored_salt = self.get_config("auth_key_salt")

        if not stored_hash or not stored_salt:
            return {"success": False, "message": "认证配置异常"}

        challenge_key = f"challenge_{timestamp}"
        if challenge_key not in self._pending_challenges:
            return {"success": False, "message": "无效的 Challenge"}

        nonce, _ = self._pending_challenges.pop(challenge_key)

        if not self._verify_response_with_stored_hash(
            stored_hash, stored_salt, nonce, timestamp, response
        ):
            return {"success": False, "message": "验证失败"}

        self.set_config("auth_enabled", "false")
        return {"success": True, "message": "认证已停用"}

    def create_challenge(self) -> dict:
        nonce = generate_nonce()
        timestamp = generate_timestamp()
        salt = self.get_config("auth_key_salt") or ""

        challenge_key = f"challenge_{timestamp}"
        self._pending_challenges[challenge_key] = (nonce, timestamp)

        return {
            "nonce": nonce,
            "timestamp": timestamp,
            "salt": salt,
        }

    def verify_login(self, response: str, timestamp: int) -> dict:
        if not self.is_auth_enabled():
            return {"success": False, "message": "认证未启用"}

        if not verify_timestamp(timestamp):
            return {"success": False, "message": "Challenge 已过期"}

        stored_hash = self.get_config("auth_key_hash")
        stored_salt = self.get_config("auth_key_salt")

        if not stored_hash or not stored_salt:
            return {"success": False, "message": "认证配置异常"}

        challenge_key = f"challenge_{timestamp}"
        if challenge_key not in self._pending_challenges:
            return {"success": False, "message": "无效的 Challenge"}

        nonce, _ = self._pending_challenges.pop(challenge_key)

        if not self._verify_response_with_stored_hash(
            stored_hash, stored_salt, nonce, timestamp, response
        ):
            return {"success": False, "message": "验证失败"}

        token = create_jwt_token(stored_hash)
        return {
            "success": True,
            "message": "登录成功",
            "token": token,
            "expires_in": JWT_EXPIRY_MINUTES * 60,
        }

    def _verify_response_with_stored_hash(
        self,
        stored_hash: str,
        stored_salt: str,
        nonce: str,
        timestamp: int,
        response: str,
    ) -> bool:
        try:
            message = f"{nonce}{timestamp}"
            # Use stored hash as the HMAC key
            expected = hmac.new(
                stored_hash.encode(), message.encode(), hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, response)
        except Exception:
            return False

    def require_auth(self, token: Optional[str]) -> bool:
        if not self.is_auth_enabled():
            return True
        if not token:
            return False
        return verify_jwt_token(token)

    def cleanup_expired_challenges(self):
        now = time.time()
        expired = [
            k
            for k, (_, ts) in self._pending_challenges.items()
            if now - ts > CHALLENGE_EXPIRY_SECONDS
        ]
        for k in expired:
            del self._pending_challenges[k]
