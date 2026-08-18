from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


class ImportRequestCreate(BaseModel):
    product_name:                    str
    product_description:             Optional[str] = None
    preferred_rental_duration_days:  int
    estimated_budget:                float
    additional_requirements:         Optional[str] = None


# ─────────────────────────────────────────
# POST /api/imports/
# Submit an "Import on Demand" request
# ─────────────────────────────────────────
@router.post("/")
async def create_import_request(
    payload:      ImportRequestCreate,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            INSERT INTO public.import_requests
                (customer_id, product_name, product_description,
                 preferred_rental_duration_days, estimated_budget,
                 additional_requirements, status)
            VALUES
                (:customer_id, :product_name, :product_description,
                 :preferred_rental_duration_days, :estimated_budget,
                 :additional_requirements, 'pending')
            RETURNING *
        """),
        {
            "customer_id":                      current_user["id"],
            "product_name":                     payload.product_name,
            "product_description":              payload.product_description,
            "preferred_rental_duration_days":    payload.preferred_rental_duration_days,
            "estimated_budget":                 payload.estimated_budget,
            "additional_requirements":          payload.additional_requirements
        }
    )
    db.commit()

    return {
        "message": "Import request submitted successfully",
        "data":    dict(result.fetchone()._mapping)
    }


# ─────────────────────────────────────────
# GET /api/imports/
# List the current user's own import requests
# ─────────────────────────────────────────
@router.get("/")
async def get_my_import_requests(
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT
                ir.*,
                cs.status as shipment_status,
                cs.tracking_notes as shipment_notes,
                cs.updated_at as shipment_updated_at
            FROM public.import_requests ir
            LEFT JOIN public.cargo_shipments cs ON cs.import_request_id = ir.id
            WHERE ir.customer_id = :customer_id
            ORDER BY ir.created_at DESC
        """),
        {"customer_id": current_user["id"]}
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}


# ─────────────────────────────────────────
# GET /api/imports/{import_id}
# Get a single import request (owner only)
# ─────────────────────────────────────────
@router.get("/{import_id}")
async def get_import_request(
    import_id:    str,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("SELECT * FROM public.import_requests WHERE id = :id"),
        {"id": import_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Import request not found")

    import_request = dict(result._mapping)

    if str(import_request["customer_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    return import_request
