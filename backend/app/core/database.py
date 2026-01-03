"""
Database operations for conversations and messages from supabase.

Provides abstraction layer for Supabase database operations with proper
error handling and type safety.
"""

from uuid import UUID
from typing import List, Optional, Dict, Any
from backend.app.schemas.message import ChatMessage
from backend.app.core.supabase_client import SupabaseClient
from fastapi import HTTPException, status


async def get_conversation(
    conversation_id: UUID, 
    user_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    Get conversation with all messages.
    
    Row Level Security ensures user can only access their own conversations.
    
    Args:
        conversation_id: UUID of the conversation
        user_id: UUID of the user (for RLS verification)
        
    Returns:
        Dict with conversation data and messages, or None if not found
        
    Raises:
        HTTPException: If database error occurs
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.table('conversations')\
            .select('*, messages(*)')\
            .eq('id', str(conversation_id))\
            .eq('user_id', str(user_id))\
            .order('messages.created_at', desc=False)\
            .single()\
            .execute()
        
        return response.data
    
    except Exception as e:
        # If not found, return None
        if "PGRST116" in str(e):  # PostgREST error code for no rows
            return None
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


async def create_conversation(
    user_id: UUID, 
    title: str = "New Chat"
) -> Dict[str, Any]:
    """
    Create new conversation for user.
    
    Args:
        user_id: UUID of the user
        title: Optional title for the conversation
        
    Returns:
        Dict with created conversation data
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.table('conversations')\
            .insert({
                'user_id': str(user_id),
                'title': title
            })\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create conversation"
            )
        
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


async def add_message(
    conversation_id: UUID,
    role: str,
    content: str
) -> Dict[str, Any]:
    """
    Add message to conversation.
    
    RLS policies ensure user can only add messages to their own conversations.
    
    Args:
        conversation_id: UUID of the conversation
        role: Message role ('system', 'user', or 'assistant')
        content: Message content
        
    Returns:
        Dict with created message data
        
    Raises:
        HTTPException: If message creation fails
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.table('messages')\
            .insert({
                'conversation_id': str(conversation_id),
                'role': role,
                'content': content
            })\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add message"
            )
        
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


async def load_conversation_messages(
    conversation_id: UUID,
    system_message: Optional[str] = None
) -> List[ChatMessage]:
    """
    Load all messages from a conversation as ChatMessage objects.
    
    Injects a system message at the beginning if provided.
    This follows the pattern used by ChatGPT where system messages
    are configuration, not persisted user data.
    
    Args:
        conversation_id: UUID of the conversation
        system_message: Optional system message to inject at the start
        
    Returns:
        List of ChatMessage objects ordered by creation time,
        with system message prepended if provided
        
    Raises:
        HTTPException: If loading fails
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.table('messages')\
            .select('role, content, created_at')\
            .eq('conversation_id', str(conversation_id))\
            .order('created_at', desc=False)\
            .execute()
        
        messages = []
        
        # Inject system message at the beginning if provided
        if system_message:
            messages.append(ChatMessage(
                role='system',
                content=system_message
            ))
        
        # Add all user and assistant messages from database
        for msg in response.data:
            messages.append(ChatMessage(
                role=msg['role'],
                content=msg['content']
            ))
        
        return messages
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load messages: {str(e)}"
        )


async def list_user_conversations(
    user_id: UUID,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List all conversations for a user.
    
    Args:
        user_id: UUID of the user
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip (for pagination)
        
    Returns:
        List of conversation dictionaries
        
    Raises:
        HTTPException: If query fails
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.table('conversations')\
            .select('id, title, created_at, updated_at')\
            .eq('user_id', str(user_id))\
            .order('updated_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return response.data
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )


async def delete_conversation(
    conversation_id: UUID,
    user_id: UUID
) -> bool:
    """
    Delete a conversation and all its messages.
    
    RLS ensures user can only delete their own conversations.
    Messages are cascade deleted automatically.
    
    Args:
        conversation_id: UUID of the conversation
        user_id: UUID of the user (for RLS verification)
        
    Returns:
        True if deleted, False if not found
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.table('conversations')\
            .delete()\
            .eq('id', str(conversation_id))\
            .eq('user_id', str(user_id))\
            .execute()
        
        return len(response.data) > 0
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


async def update_conversation_title(
    conversation_id: UUID,
    user_id: UUID,
    title: str
) -> Dict[str, Any]:
    """
    Update conversation title.
    
    Args:
        conversation_id: UUID of the conversation
        user_id: UUID of the user (for RLS verification)
        title: New title
        
    Returns:
        Updated conversation data
        
    Raises:
        HTTPException: If update fails or conversation not found
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.table('conversations')\
            .update({'title': title})\
            .eq('id', str(conversation_id))\
            .eq('user_id', str(user_id))\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}"
        )
