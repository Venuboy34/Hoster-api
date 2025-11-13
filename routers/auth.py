"""
Authentication router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
from typing import Optional
import logging

from models import (
    UserSignup, UserLogin, Token, UserResponse,
    APIKeyCreate, APIKeyResponse, UserRole
)
from config import settings
from database import get_database

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_token(data: dict, expires_delta: timedelta) -> str:
    """Create JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_api_key() -> str:
    """Generate API key"""
    return f"cdp_{secrets.token_urlsafe(settings.API_KEY_LENGTH)}"


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    db = get_database()
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Try JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        user = await db.users.find_one({"_id": user_id})
        
    except JWTError:
        # Try API key
        user = await db.users.find_one({"api_keys.key": token})
        if not user:
            raise credentials_exception
    
    if user is None:
        raise credentials_exception
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Get current admin user"""
    if current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup):
    """Register a new user"""
    db = get_database()
    
    # Check if user exists
    existing = await db.users.find_one({
        "$or": [
            {"email": user_data.email},
            {"username": user_data.username}
        ]
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create user
    user = {
        "_id": secrets.token_urlsafe(16),
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": get_password_hash(user_data.password),
        "role": UserRole.USER.value,
        "is_active": True,
        "api_keys": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await db.users.insert_one(user)
    
    logger.info(f"New user created: {user['email']}")
    
    return UserResponse(
        id=user["_id"],
        username=user["username"],
        email=user["email"],
        role=UserRole(user["role"]),
        created_at=user["created_at"],
        is_active=user["is_active"]
    )


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login user"""
    db = get_database()
    
    user = await db.users.find_one({"email": user_data.email})
    
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create tokens
    access_token = create_token(
        {"sub": user["_id"]},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_token(
        {"sub": user["_id"]},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    logger.info(f"User logged in: {user['email']}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    api_key_data: APIKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create API key"""
    db = get_database()
    
    api_key = {
        "id": secrets.token_urlsafe(16),
        "name": api_key_data.name,
        "key": create_api_key(),
        "created_at": datetime.utcnow()
    }
    
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$push": {"api_keys": api_key}}
    )
    
    logger.info(f"API key created for user: {current_user['email']}")
    
    return APIKeyResponse(**api_key)


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List user's API keys"""
    keys = current_user.get("api_keys", [])
    return [
        APIKeyResponse(
            id=key["id"],
            name=key["name"],
            key=key["key"][:10] + "..." + key["key"][-4:],  # Mask key
            created_at=key["created_at"]
        )
        for key in keys
    ]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete API key"""
    db = get_database()
    
    result = await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$pull": {"api_keys": {"id": key_id}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    logger.info(f"API key deleted for user: {current_user['email']}")
    
    return {"message": "API key deleted successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=current_user["_id"],
        username=current_user["username"],
        email=current_user["email"],
        role=UserRole(current_user["role"]),
        created_at=current_user["created_at"],
        is_active=current_user["is_active"]
    )
