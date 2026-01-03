"""
Test to check if the SupabaseClient singleton is working correctly.
"""

from backend.app.core.supabase_client import SupabaseClient
from supabase import Client


def test_supabase_singleton():
    """
    Test to check if the SupabaseClient singleton is working correctly.
    """
    # Get the singleton instance
    client = SupabaseClient.get_anon_client()
    
    # Check if the instance is a Client object
    assert isinstance(client, Client)
    
    # Check if the instance is a singleton
    assert SupabaseClient.get_anon_client() is client