"""
Authentication routes for user signup, login, and management.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from backend.app.core.supabase_client import SupabaseClient
from backend.app.core.auth import get_current_user, User
from typing import Optional

router = APIRouter()


class SignupRequest(BaseModel):
    """User signup request schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe"
            }
        }
    )
    
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(min_length=1, description="User's full name")


class LoginRequest(BaseModel):
    """User login request schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!"
            }
        }
    )
    
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response schema"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com"
                },
                "expires_in": 3600
            }
        }
    )
    
    access_token: str
    refresh_token: str
    user: dict
    expires_in: int


class RefreshRequest(BaseModel):
    """Token refresh request schema"""
    refresh_token: str


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    """
    Register a new user.
    
    Creates a new user account with email/password authentication.
    Automatically creates a user profile via database trigger.
    
    Returns:
        AuthResponse: Access token, refresh token, and user information
        
    Raises:
        HTTPException: If signup fails (e.g., email already exists)
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "full_name": request.full_name
                }
            }
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
        
        # Check if email confirmation is required
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email confirmation required. Please check your email to confirm your account."
            )
        
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email,
                "full_name": request.full_name
            },
            expires_in=response.session.expires_in or 3600
        )
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        
        # Handle common errors
        if "already registered" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {error_msg}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return tokens.
    
    Args:
        request: Login credentials (email and password)
        
    Returns:
        AuthResponse: Access token, refresh token, and user information
        
    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.user_metadata.get('full_name') if response.user.user_metadata else None
            },
            expires_in=response.session.expires_in or 3600
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    
    Access tokens expire after 1 hour. Use this endpoint to get a new
    access token without requiring the user to log in again.
    
    Args:
        request: Refresh token
        
    Returns:
        AuthResponse: New access token and refresh token
        
    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        
        response = supabase.auth.refresh_session(request.refresh_token)
        
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.user_metadata.get('full_name') if response.user.user_metadata else None
            },
            expires_in=response.session.expires_in or 3600
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token"
        )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout current user.
    
    Invalidates the current session on the server side.
    Client should also delete stored tokens.
    
    Args:
        current_user: Authenticated user (from JWT token)
        
    Returns:
        Success message
    """
    try:
        supabase = SupabaseClient.get_anon_client()
        supabase.auth.sign_out()
        
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        # Even if logout fails on server, client should delete tokens
        return {"message": "Logged out (client-side)"}


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Args:
        current_user: Authenticated user (from JWT token)
        
    Returns:
        User: Current user information
    """
    return current_user
