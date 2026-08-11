"""
Routes for Module 2 / Part 4: Waiting List Management.

Supports two styles:
1. Product-nested routes:
   - POST   /products/{product_id}/waiting-list             -> join
   - DELETE /products/{product_id}/waiting-list             -> cancel / leave
   - GET    /products/{product_id}/waiting-list/status      -> check status
2. Flat routes (requested in flow):
   - POST   /waiting-list/join?product_id={id}              -> join
   - GET    /waiting-list/position?product_id={id}          -> check status/position
   - DELETE /waiting-list/cancel?product_id={id}            -> cancel / leave
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..crud import waiting_list as wl_crud
from ..auth import get_current_user_id

# 1. Product-nested router
router = APIRouter(prefix="/products/{product_id}/waiting-list", tags=["Waiting List (Nested)"])

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
    return wl_crud.notify_next_in_queue(db, product_id)


# 2. Flat router
flat_router = APIRouter(prefix="/waiting-list", tags=["Waiting List (Flat)"])

@flat_router.post(
    "/join",
    response_model=schemas.WaitingListEntry,
    status_code=status.HTTP_201_CREATED,
    summary="Join the waiting list (Flat style)",
)
def join_flat(
    product_id: int = Query(..., description="ID of the product to wait for"),
    payload: Optional[schemas.WaitingListJoin] = None,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if payload is None:
        payload = schemas.WaitingListJoin()
    return wl_crud.join_waiting_list(db, product_id, current_user_id, payload)


@flat_router.get(
    "/position",
    response_model=schemas.WaitingListStatus,
    summary="Check waiting list status and queue position (Flat style)",
)
def get_position_flat(
    product_id: int = Query(..., description="ID of the product"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    return wl_crud.get_waiting_list_status(db, product_id, current_user_id)


@flat_router.delete(
    "/cancel",
    status_code=status.HTTP_200_OK,
    summary="Leave the waiting list (Flat style)",
)
def cancel_flat(
    product_id: int = Query(..., description="ID of the product to stop waiting for"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    return wl_crud.cancel_waiting_list(db, product_id, current_user_id)
