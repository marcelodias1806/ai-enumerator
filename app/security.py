from datetime import datetime, timedelta, timezone
from fastapi import Cookie, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.config import settings
from app.db import get_db
from app.models import User, UserRole, utcnow_naive

password_hash = PasswordHash.recommended()
COOKIE_NAME = "ai_enum_session"

ROLE_LEVEL = {UserRole.viewer: 10, UserRole.analyst: 20, UserRole.admin: 30}

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)

def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "usr": user.username,
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    user.last_login_at = utcnow_naive()
    db.commit()
    return user

def current_user(
    ai_enum_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = ai_enum_session
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="inactive user")
    return user

def require_role(minimum: UserRole):
    def dep(user: User = Depends(current_user)) -> User:
        if ROLE_LEVEL[user.role] < ROLE_LEVEL[minimum]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user
    return dep

require_viewer = require_role(UserRole.viewer)
require_analyst = require_role(UserRole.analyst)
require_admin = require_role(UserRole.admin)

def require_feed_token(
    token: str | None = Query(default=None),
    x_feed_token: str | None = Header(default=None),
):
    supplied = x_feed_token or token
    if not settings.feed_token or supplied != settings.feed_token:
        raise HTTPException(status_code=401, detail="invalid feed token")


def hash_probe_token(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
