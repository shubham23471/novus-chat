"""
Conversation management routes.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from backend.app.core.auth import get_current_user, User
from backend.app.core.database import (
    list_user_conversations,
    get_conversation,
    delete_conversation,
    update_conversation_title
)

router = APIRouter()


class ConversationListItem(BaseModel):
    """Conversation list item schema"""
    id: UUID
    title: str
    created_at: str
    updated_at: str


class ConversationDetail(BaseModel):
    """Detailed conversation with messages"""
    id: UUID
    title: str
    created_at: str
    updated_at: str
    messages: List[dict]


class UpdateTitleRequest(BaseModel):
    """Request to update conversation title"""
    title: str


@router.get("/conversations", response_model=List[ConversationListItem])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """
    List all conversations for the authenticated user.
    
    Returns conversations ordered by most recently updated first.
    
    Args:
        current_user: Authenticated user
        limit: Maximum number of conversations to return (default: 50)
        offset: Number of conversations to skip for pagination (default: 0)
        
    Returns:
        List of conversations
    """
    conversations = await list_user_conversations(
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific conversation with all messages.
    
    Args:
        conversation_id: UUID of the conversation
        current_user: Authenticated user
        
    Returns:
        Conversation with messages
        
    Raises:
        HTTPException: 404 if conversation not found or user doesn't own it
    """
    conversation = await get_conversation(conversation_id, current_user.id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: UUID of the conversation
        current_user: Authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 404 if conversation not found or user doesn't own it
    """
    deleted = await delete_conversation(conversation_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {"message": "Conversation deleted successfully"}


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    request: UpdateTitleRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update conversation title.
    
    Args:
        conversation_id: UUID of the conversation
        request: New title
        current_user: Authenticated user
        
    Returns:
        Updated conversation
        
    Raises:
        HTTPException: 404 if conversation not found or user doesn't own it
    """
    updated = await update_conversation_title(
        conversation_id=conversation_id,
        user_id=current_user.id,
        title=request.title
    )
    
    return updated
