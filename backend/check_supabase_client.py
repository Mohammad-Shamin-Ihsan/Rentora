"""
Check Supabase access using the `supabase` Python client.
Runs a simple `select` against the `reviews` table and prints the result.
"""
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

# Load env
load_dotenv(Path(__file__).resolve().parent / '.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print('ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY not set in backend/.env')
    sys.exit(2)

print('Using SUPABASE_URL:', SUPABASE_URL)

try:
    from supabase import create_client
except Exception as e:
    print('ERROR: Failed to import supabase client:', e)
    sys.exit(3)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    res = supabase.table('reviews').select('id').limit(1).execute()
    # res may be a dict-like or namedtuple depending on client version
    try:
        data = res.data if hasattr(res, 'data') else res.get('data')
        status = getattr(res, 'status_code', None) or res.get('status_code') or res.get('status')
        error = getattr(res, 'error', None) or res.get('error')
    except Exception:
        data = res
        status = None
        error = None

    print('Status:', status)
    print('Error:', error)
    print('Data (truncated):', str(data)[:1000])
    if error:
        sys.exit(4)
    sys.exit(0)
except Exception as e:
    print('ERROR: Exception while querying Supabase:', e)
    sys.exit(5)
