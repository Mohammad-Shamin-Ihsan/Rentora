from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# ─────────────────────────────────────────────────────────────────────────
# SQLAlchemy Engine Creation (Optimized for Local PostgreSQL / pgAdmin 4)
# ─────────────────────────────────────────────────────────────────────────
# Performance tuning details:
# - pool_size=20 keeps 20 persistent connections ready to serve requests instantly.
# - max_overflow=10 allows bursting up to 30 concurrent connections.
# - pool_recycle recycles connections every hour to clean up stale resources.
# - pool_timeout fails fast (10 seconds) instead of freezing the server.
# - pool_pre_ping is intentionally left out to save extra roundtrip query overhead.
engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_timeout=10
)

# ─────────────────────────────────────────────────────────────────────────
# Session Factory
# ─────────────────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ─────────────────────────────────────────────────────────────────────────
# Declarative Base for Models (SQLAlchemy 2.0 Style)
# ─────────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ─────────────────────────────────────────────────────────────────────────
# FastAPI Dependency (Injects DB Session into Route Functions)
# ─────────────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────────────────
# Startup Diagnostic Helper
# ─────────────────────────────────────────────────────────────────────────
def test_connection():
    """
    Runs a simple raw SQL check during startup to verify connectivity
    to the PostgreSQL instance.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connected successfully")
        return True
    except Exception as e:
        print("\n❌ DATABASE CONNECTION FAILED!")
        print("──────────────────────────────────────────────────────────")
        print(f"Error Details: {str(e)}")
        print("\nPossible Solutions:")
        print("1. Verify your local PostgreSQL service is running.")
        print("2. Check if the database name matches 'rentora_db' in pgAdmin 4.")
        print("3. Double check DB_PASSWORD in your backend/.env configuration.")
        print("──────────────────────────────────────────────────────────\n")
        return False