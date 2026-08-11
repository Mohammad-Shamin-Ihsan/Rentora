"""
Check direct Postgres connection using pg8000 (pure-Python driver).
"""
from pathlib import Path
import sys

# Parse .env
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
    print('ERROR: DB_HOST/DB_NAME/DB_USER not set in backend/.env')
    sys.exit(2)

print('Attempting connection to', host, 'port', port, 'db', db, 'user', user)

try:
    import pg8000
except Exception as e:
    print('ERROR: pg8000 not installed:', e)
    sys.exit(3)

try:
    conn = pg8000.connect(host=host, port=port, database=db, user=user, password=password, timeout=5)
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    val = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    if val == 1:
        print('OK: Database responded to SELECT 1')
        sys.exit(0)
    else:
        print('ERROR: unexpected response:', val)
        sys.exit(4)
except Exception as e:
    print('ERROR: Exception while connecting to DB:')
    print(e)
    sys.exit(5)
