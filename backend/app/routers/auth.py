from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, hash_password, require_auth, verify_password
from app.database.session import get_db
from app.models.models import User
from app.schemas import LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def auth_register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered.")
    user = User(email=email, full_name=payload.full_name.strip(), hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


@router.post("/login")
def auth_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")
    return {"access_token": create_access_token(user.id, user.email), "token_type": "bearer"}


@router.get("/me")
def auth_me(current_user: User = Depends(require_auth)):
    return {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name}
