from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get("/")
async def get_my_notifications(
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT * FROM public.notifications
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 50
        """),
        {"user_id": current_user["id"]}
    ).fetchall()

    unread_count = db.execute(
        text("""
            SELECT COUNT(*) FROM public.notifications
            WHERE user_id = :user_id AND is_read = false
        """),
        {"user_id": current_user["id"]}
    ).scalar()

    return {
        "data":          [dict(row._mapping) for row in result],
        "unread_count":  unread_count
    }


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user:     dict = Depends(get_current_user),
    db:                Session = Depends(get_db)
):
    result = db.execute(
        text("""
            UPDATE public.notifications
            SET is_read = true
            WHERE id = :id AND user_id = :user_id
            RETURNING id
        """),
        {"id": notification_id, "user_id": current_user["id"]}
    ).fetchone()
    db.commit()

    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Marked as read"}


@router.patch("/read-all")
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    db.execute(
        text("""
            UPDATE public.notifications
            SET is_read = true
            WHERE user_id = :user_id AND is_read = false
        """),
        {"user_id": current_user["id"]}
    )
    db.commit()
    return {"message": "All notifications marked as read"}
