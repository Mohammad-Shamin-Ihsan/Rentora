"""
Database configuration — connects to the shared Rentora database on Supabase.
Supports direct PostgreSQL (SUPABASE_DB_URL) via SQLAlchemy and Supabase SDK.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend/ directory (one level above app/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

# Fallback for local Postgres using DB_* variables if SUPABASE_DB_URL is missing
if not SUPABASE_DB_URL:
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    if all([db_user, db_pass, db_host, db_port, db_name]):
        SUPABASE_DB_URL = f"postgresql+pg8000://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

engine = None
SessionLocal = None

if SUPABASE_DB_URL:
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Initialize tables on start
        from .db_init import init_db_tables
        init_db_tables(engine)
    except Exception as e:
        print(f"Notice: Failed to initialize SQLAlchemy engine: {e}")

supabase_client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY and "your-project-ref" not in SUPABASE_URL:
    try:
        from supabase import create_client, Client
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"Notice: Failed to initialize Supabase Client: {e}")


def get_db():
    if SessionLocal:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    else:
        yield None


def get_supabase():
    return supabase_client


