from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import reviews

app = FastAPI(title="Rentora API — Ratings & Reviews")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reviews.router)


@app.get("/health")
def health():
    return {"status": "ok"}
