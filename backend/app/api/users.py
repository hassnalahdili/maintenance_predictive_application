from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.domain import normalize_role
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.models import User

from app.schemas.common import PasswordResetRequest, UserCreate, UserOut, UserUpdate
from app.services.audit import write_audit_log

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    db_user = User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        role=normalize_role(user.role),
        password_changed_at=datetime.utcnow(),
    )

    db.add(db_user)
    db.flush()
    write_audit_log(
        db,
        "create_user",
        "user",
        user=current_user,
        entity_id=db_user.id,
        request=request,
        details=db_user.email,
    )
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/technicians", response_model=list[UserOut])
def get_technicians(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    return (
        db.query(User)
        .filter(User.is_active.is_(True), User.role.in_(["admin", "technicien", "expert"]))
        .order_by(User.full_name.asc())
        .all()
    )


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    db_user = db.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    email_owner = db.query(User).filter(User.email == user.email, User.id != user_id).first()
    if email_owner:
        raise HTTPException(status_code=400, detail="Email already exists")

    db_user.full_name = user.full_name
    db_user.email = user.email
    db_user.role = normalize_role(user.role)
    db_user.is_active = user.is_active

    if user.password:
        db_user.hashed_password = get_password_hash(user.password)
        db_user.password_changed_at = datetime.utcnow()
        db_user.password_reset_required = False

    write_audit_log(
        db,
        "update_user",
        "user",
        user=current_user,
        entity_id=db_user.id,
        request=request,
        details=db_user.email,
    )
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_user_password(
    user_id: int,
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    db_user = db.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.hashed_password = get_password_hash(payload.new_password)
    db_user.password_changed_at = datetime.utcnow()
    db_user.password_reset_required = payload.require_change_on_login
    db_user.failed_login_attempts = 0
    db_user.locked_until = None
    write_audit_log(
        db,
        "reset_user_password",
        "user",
        user=current_user,
        entity_id=user_id,
        request=request,
        details=db_user.email,
    )
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    db_user = db.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

    db.delete(db_user)
    write_audit_log(
        db,
        "delete_user",
        "user",
        user=current_user,
        entity_id=user_id,
        request=request,
        details=db_user.email,
    )
    db.commit()

    return {"message": "User deleted"}
