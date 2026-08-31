from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# Create optimized engine for local development
engine = create_engine(
    settings.database_url,
    pool_size=20,           # Keep more connections hot
    max_overflow=10,
    pool_recycle=3600,
    pool_timeout=10,        # Fail fast instead of hanging
    pool_pre_ping=True      # Drop dead connections (e.g. after a DB container restart)
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
class Base(DeclarativeBase):
    pass

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Quick connection test function
def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[OK] Database connected successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False