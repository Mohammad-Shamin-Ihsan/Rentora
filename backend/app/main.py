from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, test_connection
from app.db_init import init_db_tables
from app.routers import auth, products, bookings, imports, admin, reviews, waitlist, notifications, cargo, warehouse, wishlist

app = FastAPI(
    title="Rentora API",
    description="Backend API for Rentora rental marketplace",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/auth",     tags=["Authentication"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(imports.router,  prefix="/api/imports",  tags=["Import on Demand"])
app.include_router(admin.router,    prefix="/api/admin",    tags=["Admin"])
app.include_router(reviews.router,  prefix="/api/reviews",  tags=["Reviews"])
app.include_router(waitlist.router,      prefix="/api/waitlist",      tags=["Waiting List"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(cargo.router,         prefix="/api/cargo",         tags=["Cargo Tracking"])
app.include_router(warehouse.router,     prefix="/api/warehouse",     tags=["Warehouse"])
app.include_router(wishlist.router,      prefix="/api/wishlist",      tags=["Wishlist"])

@app.on_event("startup")
async def startup_event():
    test_connection()
    init_db_tables(engine)

@app.get("/")
def health_check():
    return {"status": "Rentora API is running"}