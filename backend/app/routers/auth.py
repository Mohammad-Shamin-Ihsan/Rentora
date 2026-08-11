from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.database import get_db
from app.utils.auth_utils import create_access_token
from app.middleware.auth_middleware import get_current_user

router = APIRouter()

# ---------- Schemas ----------

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "customer"  # "customer" or "seller"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UpdateProfileRequest(BaseModel):
    full_name:    Optional[str] = None
    phone_number: Optional[str] = None

# ---------- Endpoints ----------

@router.post("/register")
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):

    # Validate role input
    allowed_roles = ["customer", "seller"]
    if payload.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Role must be either 'customer' or 'seller'"
        )

    # Check if email already exists
    existing = db.execute(
        text("SELECT id FROM public.profiles WHERE email = :email"),
        {"email": payload.email}
    ).fetchone()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists"
        )

    # Insert new user (plain password, no hashing)
    result = db.execute(
        text("""
            INSERT INTO public.profiles
                (full_name, email, password_hash, role)
            VALUES
                (:full_name, :email, :password, :role)
            RETURNING
                id, full_name, email, role, created_at
        """),
        {
            "full_name": payload.full_name,
            "email":     payload.email,
            "password":  payload.password,
            "role":      payload.role
        }
    )
    db.commit()

    user  = dict(result.fetchone()._mapping)
    token = create_access_token({"sub": str(user["id"])})

    return {
        "message":      "Account created successfully",
        "user":         user,
        "access_token": token,
        "token_type":   "bearer"
    }


@router.post("/login")
async def login(payload: LoginRequest, db: Session = Depends(get_db)):

    # Find user by email
    result = db.execute(
        text("""
            SELECT id, full_name, email, role, password_hash
            FROM public.profiles
            WHERE email = :email
        """),
        {"email": payload.email}
    ).fetchone()

    # Email not found
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    user = dict(result._mapping)

    # Check password (plain text comparison)
    if user["password_hash"] != payload.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Remove password before sending response
    user.pop("password_hash", None)

    token = create_access_token({"sub": str(user["id"])})

    return {
        "message":      "Login successful",
        "user":         user,
        "access_token": token,
        "token_type":   "bearer"
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    current_user.pop("password_hash", None)
    return current_user


@router.patch("/me")
async def update_me(
    payload:      UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    updates["id"] = current_user["id"]

    result = db.execute(
        text(f"""
            UPDATE public.profiles
            SET {set_clause}
            WHERE id = :id
            RETURNING id, full_name, email, role, phone_number, created_at
        """),
        updates
    )
    db.commit()

    return dict(result.fetchone()._mapping)
