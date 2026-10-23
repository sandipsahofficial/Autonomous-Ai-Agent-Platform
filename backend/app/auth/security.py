import hmac
import hashlib
import base64
import json
import secrets
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from app.config import get_settings


def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte cryptographically secure salt.
    Format: pbkdf2_sha256$iterations$salt_hex$hash_hex
    """
    salt = secrets.token_bytes(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against the stored PBKDF2 hash using constant-time comparison.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])
        computed_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(computed_hash, expected_hash)
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Creates a standard HS256-signed JWT token using standard cryptographic primitives.
    """
    settings = get_settings()
    secret_key = getattr(settings, "JWT_SECRET_KEY", "mesh_insecure_development_secret_change_in_production").encode("utf-8")

    to_encode = data.copy()
    now_epoch = int(time.time())
    if expires_delta:
        expire_epoch = now_epoch + int(expires_delta.total_seconds())
    else:
        expire_epoch = now_epoch + (24 * 3600)  # Default 24 hours

    to_encode.update({
        "iat": now_epoch,
        "exp": expire_epoch,
    })

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret_key, signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validates and decodes an HS256 JWT token.
    Enforces signature authenticity and expiry check.
    Returns decoded payload or None if invalid/expired.
    """
    try:
        settings = get_settings()
        secret_key = getattr(settings, "JWT_SECRET_KEY", "mesh_insecure_development_secret_change_in_production").encode("utf-8")

        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret_key, signing_input, hashlib.sha256).digest()
        provided_sig = _base64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        exp = payload.get("exp")
        if exp and int(time.time()) > int(exp):
            return None  # Token expired

        return payload
    except Exception:
        return None


def hash_api_key(api_key: str) -> str:
    """
    Cryptographic SHA-256 digest of an API key for safe database storage.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_raw_api_key(prefix: str = "mesh_sk_") -> str:
    """
    Generates a cryptographically random raw API key.
    """
    return f"{prefix}{secrets.token_urlsafe(32)}"
