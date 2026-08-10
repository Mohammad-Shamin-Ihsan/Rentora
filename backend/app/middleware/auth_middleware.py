from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.utils.auth_utils import decode_token
from app.database import get_db

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate token"
        )

    # Fetch user from database
    from sqlalchemy import text
    result = db.execute(
        text("SELECT * FROM public.profiles WHERE id = :id"),
        {"id": user_id}
    ).fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return dict(result._mapping)


def require_role(*roles: str):
    async def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {roles}"
            )
        return current_user
    return role_checker