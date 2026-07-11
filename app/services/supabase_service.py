import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client | None = None
supabase_admin: Client | None = None

if supabase_url and supabase_url != "YOUR_SUPABASE_URL":
    # Try initializing the regular client with the anon key
    if supabase_anon_key:
        try:
            supabase = create_client(supabase_url, supabase_anon_key)
        except Exception as e:
            print(f"Warning: Failed to initialize supabase client with anon key: {e}")
    
    # Fallback/default to service role key if anon client could not be initialized
    if not supabase and supabase_service_role_key:
        try:
            supabase = create_client(supabase_url, supabase_service_role_key)
            print("Using SUPABASE_SERVICE_ROLE_KEY as fallback for regular supabase client.")
        except Exception as e:
            print(f"Warning: Failed to initialize supabase client with service role key: {e}")

    # Initialize admin client
    if supabase_service_role_key:
        try:
            supabase_admin = create_client(supabase_url, supabase_service_role_key)
        except Exception as e:
            print(f"Warning: Failed to initialize supabase admin client: {e}")