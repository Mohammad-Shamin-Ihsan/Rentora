"""
Check Supabase REST access using only the Python standard library.
Prints HTTP status and a small snippet of the response.
"""
from pathlib import Path
import os
import sys
import urllib.request
import urllib.error

# Parse backend/.env without external deps
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

SUPABASE_URL = env.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = env.get('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print('ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY not set in backend/.env')
    sys.exit(2)

endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/reviews?select=*&limit=1"
headers = {
    'apikey': SUPABASE_SERVICE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
    'Accept': 'application/json'
}

req = urllib.request.Request(endpoint, headers=headers, method='GET')
print('Requesting:', endpoint)
try:
    with urllib.request.urlopen(req, timeout=20) as res:
        status = res.getcode()
        body = res.read(4096)
        print('Status:', status)
        print('Body (truncated):')
        print(body.decode('utf-8', errors='replace')[:2000])
        sys.exit(0)
except urllib.error.HTTPError as e:
    print('HTTP Error:', e.code)
    try:
        print(e.read().decode('utf-8', errors='replace')[:1000])
    except Exception:
        pass
    sys.exit(3)
except Exception as e:
    print('Error:', e)
    sys.exit(4)
