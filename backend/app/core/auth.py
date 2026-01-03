"""
Authentication middleware and utilities for FastAPI.

Provides JWT verification and user extraction for protected routes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID
from typing import Optional
from backend.app.core.supabase_client import SupabaseClient

# HTTP Bearer token security scheme
security = HTTPBearer()


class User(BaseModel):
    """Authenticated user model"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe"
            }
        }
    )
    
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None


async def verify_token(token: str) -> User:
    """
    Verify JWT token and extract user information.
    
    Args:
        token: JWT access token from Supabase
        
    Returns:
        User: Authenticated user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract user information
        user_data = user_response.user
        
        return User(
            id=UUID(user_data.id),
            email=user_data.email,
            full_name=user_data.user_metadata.get('full_name') if user_data.user_metadata else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    FastAPI dependency for protected routes.
    
    Extracts and verifies JWT token from Authorization header.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    
    Args:
        credentials: HTTP Bearer credentials from request header
        
    Returns:
        User: Authenticated user information
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    return await verify_token(token)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """
    FastAPI dependency for optionally authenticated routes.
    
    Returns user if token is provided and valid, None otherwise.
    Does not raise error if no token is provided.
    
    Usage:
        @app.get("/optional-auth")
        async def optional_route(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello anonymous"}
    
    Args:
        credentials: Optional HTTP Bearer credentials
        
    Returns:
        Optional[User]: User if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await verify_token(credentials.credentials)
    except HTTPException:
        return None
