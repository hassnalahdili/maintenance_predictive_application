from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain import normalize_role
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.models import User
from app.schemas.common import AuthResponse, ChangePasswordRequest, LoginRequest, UserCreate, UserOut
from app.services.audit import write_audit_log
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_summary(user: User) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=normalize_role(payload.role),
        password_changed_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    write_audit_log(db, "register", "user", user=user, entity_id=user.id, request=request, details=user.email)
    db.commit()
    db.refresh(user)
    return _user_summary(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        write_audit_log(db, "login_failed", "user", request=request, details=payload.email)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        write_audit_log(db, "login_blocked_inactive", "user", user=user, entity_id=user.id, request=request)
        db.commit()
        raise HTTPException(status_code=403, detail="Account inactive")

    now = datetime.utcnow()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked until {user.locked_until.isoformat()}",
        )

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
        write_audit_log(
            db,
            "login_failed",
            "user",
            user=user,
            entity_id=user.id,
            request=request,
            details=f"attempts={user.failed_login_attempts}",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user.failed_login_attempts = 0
    user.locked_until = None
    token = create_access_token({"sub": str(user.id), "role": normalize_role(user.role)})
    write_audit_log(db, "login_success", "user", user=user, entity_id=user.id, request=request)
    db.commit()
    db.refresh(user)
    return {"access_token": token, "user": _user_summary(user)}


@router.get("/password-policy")
def password_policy():
    return {
        "min_length": 8,
        "requires_uppercase": True,
        "requires_lowercase": True,
        "requires_digit": True,
        "lock_after_failed_attempts": 5,
        "lock_minutes": settings.login_lock_minutes,
    }


@router.post("/change-password", response_model=UserOut)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.get(User, current_user.id)
    if not user or not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is invalid")
    user.hashed_password = get_password_hash(payload.new_password)
    user.password_changed_at = datetime.utcnow()
    user.password_reset_required = False
    user.failed_login_attempts = 0
    user.locked_until = None
    write_audit_log(db, "change_password", "user", user=user, entity_id=user.id, request=request)
    db.commit()
    db.refresh(user)
    return user
