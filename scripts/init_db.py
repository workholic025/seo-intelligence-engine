#!/usr/bin/env python3
"""Create initial admin user if no users exist in the database."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.auth import hash_password
from app.database.session import Base, SessionLocal, engine
from app.models import models  # noqa: F401 — registers all ORM tables

Base.metadata.create_all(bind=engine)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@seo.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@SEO123")
ADMIN_NAME = os.getenv("ADMIN_NAME", "SEO Admin")

db = SessionLocal()
try:
    existing = db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first()
    if existing:
        print(f"Admin user already exists: {ADMIN_EMAIL}")
    else:
        user = models.User(
            email=ADMIN_EMAIL,
            full_name=ADMIN_NAME,
            hashed_password=hash_password(ADMIN_PASSWORD),
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print("IMPORTANT: Change this password after first login.")
finally:
    db.close()
