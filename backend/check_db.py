"""
Simple DB connection checker for the backend.
Usage:
  cd backend
  venv\Scripts\activate
  pip install -r requirements.txt
  python check_db.py

Exits with code 0 on success, non-zero on failure.
"""

from pathlib import Path
import os
import sys
from sqlalchemy import create_engine, text

# Parse backend/.env without python-dotenv
env_path = Path(__file__).resolve().parent / ".env"
env = {}
if env_path.exists():
    for line in env_path.read_text(encoding='utf8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

SUPABASE_DB_URL = env.get("SUPABASE_DB_URL")
if not SUPABASE_DB_URL:
    db_user = env.get("DB_USER")
    db_pass = env.get("DB_PASSWORD")
    db_host = env.get("DB_HOST")
    db_port = env.get("DB_PORT")
    db_name = env.get("DB_NAME")
    if all([db_user, db_pass, db_host, db_port, db_name]):
        SUPABASE_DB_URL = f"postgresql+pg8000://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

if not SUPABASE_DB_URL:
    print("ERROR: SUPABASE_DB_URL or individual DB configuration variables are not set in backend/.env")
    sys.exit(2)

print("Using SUPABASE_DB_URL:", "(hidden)" if SUPABASE_DB_URL else "(empty)")

try:
    engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        r = conn.execute(text("SELECT 1"))
        val = r.scalar()
    if val == 1:
        print("OK: Database responded to SELECT 1")
        sys.exit(0)
    else:
        print("ERROR: Unexpected result from SELECT 1:", val)
        sys.exit(3)
except Exception as e:
    print("ERROR: Exception while connecting to database:")
    print(e)
    sys.exit(4)
