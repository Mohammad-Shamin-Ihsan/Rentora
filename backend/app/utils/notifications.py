from sqlalchemy.orm import Session
from sqlalchemy import text


def notify(db: Session, user_id: str, title: str, message: str) -> None:
    """
    Create an in-app notification. This is the "mock" stand-in for the
    real Gmail/SMS integration mentioned in the spec: no email/SMS is
    actually sent, but the event is recorded so it can be shown in the
    notifications inbox.
    """
    db.execute(
        text("""
            INSERT INTO public.notifications (user_id, title, message)
            VALUES (:user_id, :title, :message)
        """),
        {"user_id": user_id, "title": title, "message": message}
    )


def notify_waitlist(db: Session, product_id: str) -> int:
    """
    Notify everyone still 'waiting' on this product, in the order they
    joined, and mark them 'notified'. Returns how many were notified.
    Caller is responsible for db.commit().
    """
    product = db.execute(
        text("SELECT title FROM public.products WHERE id = :id"),
        {"id": product_id}
    ).fetchone()

    if not product:
        return 0

    waiters = db.execute(
        text("""
            SELECT id, customer_id FROM public.waiting_lists
            WHERE product_id = :product_id AND status = 'waiting'
            ORDER BY joined_at ASC
        """),
        {"product_id": product_id}
    ).fetchall()

    for waiter in waiters:
        notify(
            db,
            str(waiter.customer_id),
            "Item now available",
            f'"{product.title}" is available again — book it before someone else does!'
        )
        db.execute(
            text("UPDATE public.waiting_lists SET status = 'notified' WHERE id = :id"),
            {"id": waiter.id}
        )

    return len(waiters)
