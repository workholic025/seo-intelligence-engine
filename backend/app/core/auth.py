import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.models import User

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def create_access_token(user_id: int, email: str, expires_seconds: int = 604800) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = {"sub": str(user_id), "email": email, "exp": int(time.time()) + expires_seconds}
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig_input = f"{header}.{body}".encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def _decode_token(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed token")
    header, body, sig_b64 = parts
    expected = hmac.new(settings.SECRET_KEY.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        raise ValueError("Invalid signature")
    payload = json.loads(_b64url_decode(body))
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("Token expired")
    return payload


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return f"pbkdf2:sha256:260000:{salt}:{dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        _, algo, iters, salt, dk_hex = hashed.split(":", 4)
        dk = hashlib.pbkdf2_hmac(algo, password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def get_current_user_optional(
    token: Optional[str] = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = _decode_token(token)
        return db.query(User).filter(User.id == int(payload["sub"]), User.is_active.is_(True)).first()
    except Exception:
        return None


def require_auth(user: Optional[User] = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
