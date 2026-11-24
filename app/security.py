"""Password hashing and short-lived signed bearer tokens for staff access."""
import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User


TOKEN_SECRET = os.getenv("AUTH_SECRET", "development-only-change-this-secret")
TOKEN_TTL_SECONDS = 8 * 60 * 60



def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_text, digest_text = encoded.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_text)
        expected = base64.urlsafe_b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_token(user: User) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user.id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}).encode()).decode().rstrip("=")
    signature = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload}.{sig}"


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in")
    try:
        payload, signature = authorization[7:].split(".", 1)
        expected = base64.urlsafe_b64encode(
            hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data["exp"] < time.time():
            raise ValueError("expired")
        user = db.get(User, int(data["sub"]))
        if not user or not user.is_active:
            raise ValueError("inactive")
        return user
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid; please sign in again")


def require_staff(user: User = Depends(current_user)) -> User:
    if user.role not in {"admin", "staff"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff access required")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user
