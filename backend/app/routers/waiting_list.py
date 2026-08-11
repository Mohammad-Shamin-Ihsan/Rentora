"""
Routes for Module 2 / Part 4: Waiting List Management.

  POST   /products/{product_id}/waiting-list             -> join
  DELETE /products/{product_id}/waiting-list             -> cancel / leave
  GET    /products/{product_id}/waiting-list/status      -> check own status
  GET    /products/{product_id}/waiting-list             -> list all pending (admin)
  POST   /products/{product_id}/waiting-list/notify      -> trigger notifications when product becomes available
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..crud import waiting_list as wl_crud
from ..auth import get_current_user_id

router = APIRouter(prefix="/products/{product_id}/waiting-list", tags=["Waiting List"])


@router.post(
    "",
    response_model=schemas.WaitingListEntry,
    status_code=status.HTTP_201_CREATED,
    summary="Join the waiting list for an unavailable product",
)
def join_waiting_list(
    product_id: int,
    payload: schemas.WaitingListJoin,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Adds the current user to the waiting list for `product_id`.
    Returns the created entry including their queue position.
    """
    return wl_crud.join_waiting_list(db, product_id, current_user_id, payload)


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    summary="Leave the waiting list",
)
def cancel_waiting_list(
    product_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Removes the current user's pending entry from the waiting list."""
    return wl_crud.cancel_waiting_list(db, product_id, current_user_id)


@router.get(
    "/status",
    response_model=schemas.WaitingListStatus,
    summary="Check if you are on the waiting list",
)
def get_waiting_list_status(
    product_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Returns whether the user is on the list and their queue position."""
    return wl_crud.get_waiting_list_status(db, product_id, current_user_id)


@router.get(
    "",
    response_model=List[schemas.WaitingListEntry],
    summary="List all pending users (admin / staff view)",
)
def list_waiting_list(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Returns the full ordered queue for a product. No auth needed for demo."""
    return wl_crud.list_waiting_list(db, product_id)


@router.post(
    "/notify",
    status_code=status.HTTP_200_OK,
    summary="Notify waiting list when product becomes available",
)
def notify_waiting_list(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Triggers notifications (in-app + email if configured) for all pending
    users on the waiting list for this product.
    Call this endpoint when a product's status changes to 'available'.
    No auth for demo — in production restrict to admin/warehouse staff role.
    """
    return wl_crud.notify_next_in_queue(db, product_id)
