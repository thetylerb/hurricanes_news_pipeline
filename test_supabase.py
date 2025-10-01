import os
from dotenv import load_dotenv
from supabase import create_client
import datetime

# load your .env
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(url, key)

print("✅ Connected to Supabase at:", url)

# --- Test 1: SELECT (read) ---
try:
    result = supabase.table("articles").select("*").limit(3).execute()
    print("SELECT works. Rows returned:", len(result.data))
    print(result.data)  # might be [] if empty, that’s fine
except Exception as e:
    print("❌ SELECT failed:", e)

# --- Test 2: INSERT (write) ---
test_id = "test_" + datetime.datetime.utcnow().isoformat()
try:
    insert_result = supabase.table("articles").insert({
        "id": test_id,
        "title": "Test article",
        "author": "PipelineTester",
        "published_at": datetime.datetime.utcnow().isoformat(),
        "summary": "This is just a test insert.",
        "tags": ["test"],
        "source_url": "http://example.com/test",
        "extracted_at": datetime.datetime.utcnow().isoformat()
    }).execute()
    print("INSERT works. Insert result:", insert_result.data)
except Exception as e:
    print("❌ INSERT failed:", e)

# --- Test 3: SELECT again to confirm our insert is visible ---
try:
    check = supabase.table("articles").select("*").eq("id", test_id).execute()
    print("Row we just inserted:", check.data)
except Exception as e:
    print("❌ SELECT-after-insert failed:", e)
