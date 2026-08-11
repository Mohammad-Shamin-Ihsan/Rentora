"""
CRUD + business logic for Module 2 / Part 4: Waiting List Management.

Table: public.waiting_list
  id, product_id, user_id, joined_at, notified_at, status
  status ∈ {'pending', 'notified', 'cancelled'}

Notification strategy (MVP):
  - We store a notification row in public.notifications (already in schema).
  - If Gmail is configured in future, plug the SMTP call into _send_email().
"""

from __future__ import annotations

import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import schemas


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_user_email(db: Session, user_id: int) -> Optional[str]:
    """Return the registered email for a user, or None if not found."""
    row = db.execute(
        text("SELECT email FROM public.users WHERE id = :uid"),
        {"uid": user_id},
    ).fetchone()
    return row[0] if row else None


def _get_product_name(db: Session, product_id: int) -> str:
    """Return the product name, falling back to 'the product'."""
    row = db.execute(
        text("SELECT name FROM public.products WHERE id = :pid"),
        {"pid": product_id},
    ).fetchone()
    return row[0] if row else "the product"


def _send_email(to_email: str, product_name: str) -> None:
    """
    Attempt to send a Gmail notification.
    Reads GMAIL_SENDER / GMAIL_APP_PASSWORD from environment.
    If credentials are missing or sending fails, we log but do NOT crash —
    the notification row in public.notifications is the reliable fallback.
    """
    sender = os.getenv("GMAIL_SENDER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not sender or not app_password:
        print("Notice: Gmail credentials not configured — skipping email send.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Good news! '{product_name}' is now available on Rentora"
        msg["From"] = sender
        msg["To"] = to_email

        html_body = f"""
        <html><body style="font-family:sans-serif;color:#1a1a1a;">
          <h2 style="color:#6d28d9;">Great news! 🎉</h2>
          <p>The product <strong>'{product_name}'</strong> you added to your
          waiting list is now <strong>available for rental</strong> on Rentora.</p>
          <p>Log in now to book it before someone else does!</p>
          <a href="http://localhost:4200" style="display:inline-block;padding:10px 20px;
             background:#6d28d9;color:#fff;border-radius:6px;text-decoration:none;">
            Book Now →
          </a>
          <p style="margin-top:24px;font-size:12px;color:#888;">
            You received this because you joined the waiting list on Rentora.
          </p>
        </body></html>
        """
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, app_password)
            smtp.sendmail(sender, to_email, msg.as_string())
        print(f"Notification email sent to {to_email}")
    except Exception as exc:
        print(f"Warning: Failed to send notification email to {to_email}: {exc}")


def _store_notification(db: Session, user_id: int, message: str) -> None:
    """Persist a notification row for the user (in-app inbox)."""
    db.execute(
        text(
            "INSERT INTO public.notifications (user_id, message, sent_at, is_read) "
            "VALUES (:uid, :msg, :now, false)"
        ),
        {"uid": user_id, "msg": message, "now": _utcnow()},
    )


# ---------------------------------------------------------------------------
# Public API — called by the router
# ---------------------------------------------------------------------------

def join_waiting_list(
    db: Session,
    product_id: int,
    user_id: int,
    payload: schemas.WaitingListJoin,
) -> schemas.WaitingListEntry:
    """
    Add user to the waiting list for a product.
    Raises 400 if the product is still available (no need to wait).
    Raises 409 if the user already has a pending entry.
    """
    # 1. Verify product exists and is NOT available
    product_row = db.execute(
        text("SELECT id, status FROM public.products WHERE id = :pid"),
        {"pid": product_id},
    ).fetchone()
    if not product_row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {product_id} not found.")

    if product_row[1] == "available":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This product is currently available — you can book it directly!",
        )

    # 2. Check for an existing active (pending/notified) entry
    existing = db.execute(
        text(
            "SELECT id FROM public.waiting_list "
            "WHERE product_id = :pid AND user_id = :uid "
            "AND status IN ('pending', 'notified')"
        ),
        {"pid": product_id, "uid": user_id},
    ).fetchone()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You are already on the waiting list for this product.",
        )

    # 3. Insert the new entry
    row = db.execute(
        text(
            "INSERT INTO public.waiting_list "
            "(product_id, user_id, joined_at, status) "
            "VALUES (:pid, :uid, :now, 'pending') "
            "RETURNING id, product_id, user_id, joined_at, notified_at, status"
        ),
        {"pid": product_id, "uid": user_id, "now": _utcnow()},
    ).fetchone()
    db.commit()

    queue_pos = _queue_position(db, product_id, row[0])
    return schemas.WaitingListEntry(
        id=row[0],
        product_id=row[1],
        user_id=row[2],
        joined_at=row[3],
        notified_at=row[4],
        status=row[5],
        queue_position=queue_pos,
    )


def cancel_waiting_list(db: Session, product_id: int, user_id: int) -> Dict[str, Any]:
    """Mark the user's pending entry as cancelled."""
    result = db.execute(
        text(
            "UPDATE public.waiting_list "
            "SET status = 'cancelled' "
            "WHERE product_id = :pid AND user_id = :uid AND status = 'pending' "
            "RETURNING id"
        ),
        {"pid": product_id, "uid": user_id},
    ).fetchone()
    db.commit()

    if not result:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No active waiting list entry found for this product.",
        )
    return {"message": "You have been removed from the waiting list.", "id": result[0]}


def get_waiting_list_status(
    db: Session, product_id: int, user_id: int
) -> schemas.WaitingListStatus:
    """Return whether the user is on the waiting list and their queue position."""
    row = db.execute(
        text(
            "SELECT id, product_id, user_id, joined_at, notified_at, status "
            "FROM public.waiting_list "
            "WHERE product_id = :pid AND user_id = :uid "
            "AND status IN ('pending', 'notified') "
            "ORDER BY joined_at DESC LIMIT 1"
        ),
        {"pid": product_id, "uid": user_id},
    ).fetchone()

    pending_count_row = db.execute(
        text(
            "SELECT COUNT(*) FROM public.waiting_list "
            "WHERE product_id = :pid AND status = 'pending'"
        ),
        {"pid": product_id},
    ).fetchone()
    pending_count = pending_count_row[0] if pending_count_row else 0

    if not row:
        return schemas.WaitingListStatus(on_list=False, entry=None, pending_count=pending_count)

    queue_pos = _queue_position(db, product_id, row[0]) if row[5] == "pending" else None
    entry = schemas.WaitingListEntry(
        id=row[0],
        product_id=row[1],
        user_id=row[2],
        joined_at=row[3],
        notified_at=row[4],
        status=row[5],
        queue_position=queue_pos,
    )
    return schemas.WaitingListStatus(on_list=True, entry=entry, pending_count=pending_count)


def list_waiting_list(
    db: Session, product_id: int
) -> List[schemas.WaitingListEntry]:
    """Return all pending entries for a product in queue order (admin view)."""
    rows = db.execute(
        text(
            "SELECT id, product_id, user_id, joined_at, notified_at, status "
            "FROM public.waiting_list "
            "WHERE product_id = :pid AND status = 'pending' "
            "ORDER BY joined_at ASC"
        ),
        {"pid": product_id},
    ).fetchall()

    entries = []
    for idx, row in enumerate(rows, start=1):
        entries.append(
            schemas.WaitingListEntry(
                id=row[0],
                product_id=row[1],
                user_id=row[2],
                joined_at=row[3],
                notified_at=row[4],
                status=row[5],
                queue_position=idx,
            )
        )
    return entries


def notify_next_in_queue(db: Session, product_id: int) -> Dict[str, Any]:
    """
    Called when a product becomes available.
    Notifies ALL pending users (email + in-app notification) in queue order
    and marks their entries as 'notified'.

    In a real system you might notify only the first person; here we notify
    all so they can compete to book.
    """
    product_name = _get_product_name(db, product_id)

    rows = db.execute(
        text(
            "SELECT id, user_id FROM public.waiting_list "
            "WHERE product_id = :pid AND status = 'pending' "
            "ORDER BY joined_at ASC"
        ),
        {"pid": product_id},
    ).fetchall()

    if not rows:
        return {"notified": 0, "message": "No users on the waiting list."}

    notified_ids: List[int] = []
    for row in rows:
        entry_id, user_id = row[0], row[1]

        # Mark as notified
        db.execute(
            text(
                "UPDATE public.waiting_list "
                "SET status = 'notified', notified_at = :now "
                "WHERE id = :eid"
            ),
            {"eid": entry_id, "now": _utcnow()},
        )

        # Store in-app notification
        message = (
            f"Great news! '{product_name}' is now available for rental. "
            f"Book it now before it's gone!"
        )
        _store_notification(db, user_id, message)

        # Attempt Gmail notification
        email = _get_user_email(db, user_id)
        if email:
            _send_email(email, product_name)

        notified_ids.append(user_id)

    db.commit()
    return {
        "notified": len(notified_ids),
        "message": f"Notified {len(notified_ids)} user(s) on the waiting list.",
        "user_ids": notified_ids,
    }


# ---------------------------------------------------------------------------
# Internal utility
# ---------------------------------------------------------------------------

def _queue_position(db: Session, product_id: int, entry_id: int) -> Optional[int]:
    """Return 1-based queue position of a given entry among pending entries."""
    rows = db.execute(
        text(
            "SELECT id FROM public.waiting_list "
            "WHERE product_id = :pid AND status = 'pending' "
            "ORDER BY joined_at ASC"
        ),
        {"pid": product_id},
    ).fetchall()
    for idx, row in enumerate(rows, start=1):
        if row[0] == entry_id:
            return idx
    return None
