import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middleware.auth_middleware import require_role
from app.utils.notifications import notify

router = APIRouter()

VALID_CARGO_STATUSES = ["purchased", "in_transit", "customs_cleared", "arrived"]


class ShipmentStatusUpdate(BaseModel):
    status:          str
    tracking_notes:  Optional[str] = None


@router.get("/shipments")
async def get_shipments(
    current_user: dict = Depends(require_role("cargo_manager", "admin")),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT
                cs.*,
                ir.product_name, ir.product_description, ir.estimated_budget,
                ir.preferred_rental_duration_days,
                pr.full_name as customer_name, pr.email as customer_email
            FROM public.cargo_shipments cs
            JOIN public.import_requests ir ON cs.import_request_id = ir.id
            JOIN public.profiles pr ON ir.customer_id = pr.id
            ORDER BY cs.created_at DESC
        """)
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}


@router.patch("/shipments/{shipment_id}")
async def update_shipment_status(
    shipment_id:  str,
    payload:      ShipmentStatusUpdate,
    current_user: dict = Depends(require_role("cargo_manager", "admin")),
    db:           Session = Depends(get_db)
):
    if payload.status not in VALID_CARGO_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {VALID_CARGO_STATUSES}")

    shipment = db.execute(
        text("""
            SELECT cs.*, ir.product_name, ir.product_description, ir.estimated_budget,
                   ir.preferred_rental_duration_days, ir.additional_requirements,
                   ir.customer_id
            FROM public.cargo_shipments cs
            JOIN public.import_requests ir ON cs.import_request_id = ir.id
            WHERE cs.id = :id
        """),
        {"id": shipment_id}
    ).fetchone()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    result = db.execute(
        text("""
            UPDATE public.cargo_shipments
            SET status = :status, tracking_notes = :tracking_notes, cargo_manager_id = :cargo_manager_id
            WHERE id = :id
            RETURNING *
        """),
        {
            "status":           payload.status,
            "tracking_notes":   payload.tracking_notes,
            "cargo_manager_id": current_user["id"],
            "id":               shipment_id
        }
    ).fetchone()

    status_labels = {
        "purchased":       "Purchased from supplier",
        "in_transit":      "In transit",
        "customs_cleared": "Cleared customs",
        "arrived":         "Arrived at our warehouse",
    }
    notify(
        db, str(shipment.customer_id), "Shipment update",
        f'"{shipment.product_name}" — {status_labels[payload.status]}.'
    )

    new_product = None
    if payload.status == "arrived":
        # Item has physically arrived — add it to the bookable rental inventory
        # and close out the import request. Pricing is a simple heuristic off
        # the customer's estimated budget since there's no supplier invoice step.
        rental_price_per_day = round(float(shipment.estimated_budget) * 0.015, 2)
        security_deposit      = round(float(shipment.estimated_budget) * 0.5, 2)

        specs = {}
        if shipment.additional_requirements:
            specs["notes"] = shipment.additional_requirements

        new_row = db.execute(
            text("""
                INSERT INTO public.products
                    (title, description, technical_specifications,
                     rental_price_per_day, security_deposit, condition, status, images)
                VALUES
                    (:title, :description, :specs, :price, :deposit, 'new', 'available', '{}')
                RETURNING id, title
            """),
            {
                "title":       shipment.product_name,
                "description": shipment.product_description or f"Freshly imported: {shipment.product_name}.",
                "specs":       json.dumps(specs),
                "price":       rental_price_per_day,
                "deposit":     security_deposit
            }
        ).fetchone()
        new_product = dict(new_row._mapping)

        db.execute(
            text("UPDATE public.import_requests SET status = 'completed' WHERE id = :id"),
            {"id": shipment.import_request_id}
        )
        notify(
            db, str(shipment.customer_id), "Ready to book",
            f'"{shipment.product_name}" has arrived and is now available to book!'
        )

    db.commit()

    return {
        "message":     f"Shipment status updated to '{payload.status}'",
        "shipment":    dict(result._mapping),
        "new_product": new_product
    }
