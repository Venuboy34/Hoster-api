"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class AppStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    DEPLOYING = "deploying"
    PENDING = "pending"


class DeploymentSource(str, Enum):
    GITHUB = "github"
    DOCKER = "docker"
    PYTHON_SCRIPT = "python_script"


class FunctionRuntime(str, Enum):
    PYTHON = "python"
    NODEJS = "nodejs"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


# User Models
class UserSignup(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v:
            raise ValueError('Username must be alphanumeric with optional underscores')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    is_active: bool


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    created_at: datetime


# Token Models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None


# App Models
class AppCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None
    source_type: DeploymentSource
    source_config: Dict[str, Any]
    env_vars: Optional[Dict[str, str]] = {}
    
    @validator('name')
    def validate_name(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Name must be alphanumeric with hyphens or underscores')
        return v.lower()


class AppUpdate(BaseModel):
    description: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    status: Optional[AppStatus] = None


class AppResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    user_id: str
    status: AppStatus
    source_type: DeploymentSource
    source_config: Dict[str, Any]
    env_vars: Dict[str, str]
    url: str
    created_at: datetime
    updated_at: datetime


# Deployment Models
class DeploymentCreate(BaseModel):
    app_id: str
    commit_sha: Optional[str] = None
    docker_image: Optional[str] = None


class DeploymentResponse(BaseModel):
    id: str
    app_id: str
    user_id: str
    status: AppStatus
    commit_sha: Optional[str]
    docker_image: Optional[str]
    logs: List[str] = []
    created_at: datetime
    completed_at: Optional[datetime] = None


# Function Models
class FunctionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    runtime: FunctionRuntime
    code: str
    handler: str = "main"
    env_vars: Optional[Dict[str, str]] = {}
    timeout: int = Field(default=30, ge=1, le=300)


class FunctionUpdate(BaseModel):
    code: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    timeout: Optional[int] = Field(None, ge=1, le=300)


class FunctionResponse(BaseModel):
    id: str
    name: str
    user_id: str
    runtime: FunctionRuntime
    handler: str
    env_vars: Dict[str, str]
    timeout: int
    endpoint: str
    created_at: datetime
    updated_at: datetime


class FunctionInvoke(BaseModel):
    payload: Optional[Dict[str, Any]] = {}


# Log Models
class LogEntry(BaseModel):
    message: str
    level: str = "info"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LogResponse(BaseModel):
    id: str
    app_id: Optional[str] = None
    deployment_id: Optional[str] = None
    function_id: Optional[str] = None
    log_type: str
    message: str
    level: str
    created_at: datetime


# Admin Models
class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UsageMetrics(BaseModel):
    user_id: str
    app_count: int
    deployment_count: int
    function_count: int
    total_requests: int
    created_at: datetime


# Generic Response
class MessageResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None
