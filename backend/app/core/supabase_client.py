"""
Supabase client singleton for the application.

Provides two client instances:
- Anon client: For user-scoped operations (respects RLS)
- Service client: For admin operations (bypasses RLS)
"""

from supabase import create_client, Client
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class SupabaseClient:
    """Singleton Supabase client manager"""
    
    _anon_client: Optional[Client] = None
    _service_client: Optional[Client] = None
    
    @classmethod
    def get_anon_client(cls) -> Client:
        """
        Get client for user-scoped operations.
        
        This client respects Row Level Security (RLS) policies.
        Safe to use with user JWT tokens.
        
        Returns:
            Client: Supabase client with anon key
        """
        if cls._anon_client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_ANON_KEY")
            
            if not url or not key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment"
                )
            
            cls._anon_client = create_client(url, key)
        
        return cls._anon_client
    
    @classmethod
    def get_service_client(cls) -> Client:
        """
        Get client for admin operations.
        
        WARNING: This client BYPASSES Row Level Security!
        Only use for administrative tasks that require elevated privileges.
        Never expose this client to user requests directly.
        
        Returns:
            Client: Supabase client with service role key
        """
        if cls._service_client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            
            if not url or not key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment"
                )
            
            cls._service_client = create_client(url, key)
        
        return cls._service_client
    
    @classmethod
    def reset_clients(cls):
        """Reset client instances (useful for testing)"""
        cls._anon_client = None
        cls._service_client = None
