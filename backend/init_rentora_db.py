"""
Create the Rentora database if it does not already exist.
Uses local Postgres credentials from backend/.env.
"""
from pathlib import Path
import sys

env_path = Path(__file__).resolve().parent / '.env'
env = {}
if env_path.exists():
    for line in env_path.read_text(encoding='utf8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

host = env.get('DB_HOST')
port = int(env.get('DB_PORT') or 5432)
db = env.get('DB_NAME')
user = env.get('DB_USER')
password = env.get('DB_PASSWORD')

if not (host and db and user):
    print('ERROR: DB_HOST, DB_NAME, and DB_USER must be set in backend/.env')
    sys.exit(2)

print('Connecting to Postgres host', host, 'port', port, 'as user', user)
try:
    import pg8000
except Exception as e:
    print('ERROR: pg8000 is not installed:', e)
    sys.exit(3)

try:
    conn = pg8000.connect(host=host, port=port, database='postgres', user=user, password=password, timeout=10)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
    row = cursor.fetchone()
    if row is not None and row[0] == 1:
        print(f'Database {db!r} already exists.')
    else:
        print(f'Creating database {db!r}...')
        cursor.execute(f'CREATE DATABASE "{db}"')
        print('Created database', db)
    cursor.close()
    conn.close()
    sys.exit(0)
except Exception as e:
    print('ERROR: Failed to create or verify database:')
    print(e)
    sys.exit(4)
