import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

print("=== Backend Connection Test ===\n")

# Test 1: Read categories (public table)
try:
    result = supabase.table("categories").select("*").execute()
    print(f"✅ Categories: {len(result.data)} rows found")
    for cat in result.data:
        print(f"   - {cat['name']}")
except Exception as e:
    print(f"❌ Categories failed: {e}")

print()

# Test 2: Read profiles
try:
    result = supabase.table("profiles").select("count").limit(1).execute()
    print(f"✅ Profiles table accessible")
except Exception as e:
    print(f"❌ Profiles failed: {e}")

print()

# Test 3: Read products
try:
    result = supabase.table("products").select("count").limit(1).execute()
    print(f"✅ Products table accessible ({len(result.data)} rows)")
except Exception as e:
    print(f"❌ Products failed: {e}")

print()

# Test 4: Read bookings (should work with service_role)
try:
    result = supabase.table("bookings").select("count").limit(1).execute()
    print(f"✅ Bookings table accessible")
except Exception as e:
    print(f"❌ Bookings failed: {e}")

print()

# Test 5: Read import_requests
try:
    result = supabase.table("import_requests").select("count").limit(1).execute()
    print(f"✅ Import requests table accessible")
except Exception as e:
    print(f"❌ Import requests failed: {e}")

print()

# Test 6: Verify service_role key
import base64, json
parts = key.split('.')
if len(parts) == 3:
    padding = 4 - len(parts[1]) % 4
    payload = json.loads(
        base64.urlsafe_b64decode(parts[1] + '=' * padding)
    )
    role = payload.get('role', 'unknown')
    if role == 'service_role':
        print(f"✅ Using service_role key (correct for backend)")
    else:
        print(f"⚠️  Key role is '{role}' — backend should use service_role key")

print("\n=== All backend tests complete ===")
