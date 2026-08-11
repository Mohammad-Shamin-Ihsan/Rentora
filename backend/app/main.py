from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import reviews, waiting_list

app = FastAPI(title="Rentora API — Module 1 Part 4 + Module 2 Part 4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reviews.router)
app.include_router(waiting_list.router)
app.include_router(waiting_list.flat_router)


@app.get("/health")
def health():
    return {"status": "ok"}
