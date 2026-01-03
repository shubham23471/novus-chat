from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

supabase: Client = create_client(url, key)

# Test connection
try:
    # Try to query profiles table
    response = supabase.table('profiles').select("*").limit(1).execute()
    print("✅ Successfully connected to Supabase!")
    print(f"Response: {response}")
except Exception as e:
    print(f"❌ Connection failed: {e}")