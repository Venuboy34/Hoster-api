"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from typing import List
import secrets


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Cloud Deployment Platform"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    API_KEY_LENGTH: int = 32
    
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "cloud_deploy_platform"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    USE_REDIS: bool = False
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Docker
    DOCKER_REGISTRY: str = "registry.hub.docker.com"
    DEFAULT_DOCKER_IMAGE: str = "python:3.11-slim"
    
    # Deployment
    BASE_DOMAIN: str = "myplatform.app"
    DEPLOYMENT_TIMEOUT: int = 600  # seconds
    MAX_APPS_PER_USER: int = 10
    
    # Storage
    LOGS_RETENTION_DAYS: int = 30
    MAX_LOG_SIZE_MB: int = 100
    
    # Email (Optional)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@myplatform.app"
    EMAIL_ENABLED: bool = False
    
    # GitHub OAuth (Optional)
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_ENABLED: bool = False
    
    # Admin
    ADMIN_EMAIL: str = "admin@myplatform.app"
    ADMIN_PASSWORD: str = "changeme123"
    
    # Celery (Optional)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    USE_CELERY: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
