from sqlalchemy import select
from app.config import settings
from app.db import SessionLocal
from app.models import User, UserRole
from app.security import hash_password

if settings.bootstrap_admin_password in {"change-me-now", "password", "admin"}:
    print("WARNING: BOOTSTRAP_ADMIN_PASSWORD is still using an insecure default.")

with SessionLocal() as db:
    user = db.scalar(select(User).where(User.username == settings.bootstrap_admin_username))
    if not user:
        user = User(
            username=settings.bootstrap_admin_username,
            password_hash=hash_password(settings.bootstrap_admin_password),
            role=UserRole.admin,
            is_active=True,
        )
        db.add(user); db.commit()
        print(f"Bootstrap admin created: {user.username}")
    else:
        print(f"Bootstrap admin already exists: {user.username}")
