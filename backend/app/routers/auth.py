from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from app.database import get_db

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

    user = dict(result.fetchone()._mapping)

    return {
        "message": "Account created successfully",
        "user": user
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

    return {
        "message": "Login successful",
        "user": user
    }


@router.get("/me/{user_id}")
async def get_me(user_id: str, db: Session = Depends(get_db)):

    result = db.execute(
        text("""
            SELECT id, full_name, email, role, phone_number, created_at
            FROM public.profiles
            WHERE id = :id
        """),
        {"id": user_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return dict(result._mapping)