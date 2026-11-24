from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User
from app.security import create_token, current_user, hash_password, require_admin, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class StaffCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


def user_data(user: User):
    return {"id": user.id, "username": user.username, "role": user.role}


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))

    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            401,
            "Incorrect username or password"
        )
    
    return {"access_token": create_token(user), "token_type": "bearer", "user": user_data(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_data(user)


@router.post("/staff", status_code=201)
def create_staff(data: StaffCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    user = User(username=data.username.strip(), password_hash=hash_password(data.password), role="staff")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That username is already in use")
    db.refresh(user)
    return user_data(user)


@router.get("/staff")
def list_staff(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return [user_data(user) for user in db.scalars(select(User).where(User.role == "staff").order_by(User.username))]
