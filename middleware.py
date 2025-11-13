"""
Custom middleware
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict
import logging

from config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit_store: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host
        
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)
        
        current_time = time.time()
        
        # Initialize or clean old requests
        if client_ip not in self.rate_limit_store:
            self.rate_limit_store[client_ip] = []
        
        # Remove old requests outside time window
        self.rate_limit_store[client_ip] = [
            req_time for req_time in self.rate_limit_store[client_ip]
            if current_time - req_time < settings.RATE_LIMIT_WINDOW
        ]
        
        # Check rate limit
        if len(self.rate_limit_store[client_ip]) >= settings.RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Add current request
        self.rate_limit_store[client_ip].append(current_time)
        
        response = await call_next(request)
        return response
