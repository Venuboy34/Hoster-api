"""
Serverless functions router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Any
from datetime import datetime
import secrets
import logging

from models import (
    FunctionCreate, FunctionUpdate, FunctionResponse,
    FunctionInvoke, FunctionRuntime
)
from routers.auth import get_current_user
from config import settings
from database import get_database

logger = logging.getLogger(__name__)
router = APIRouter()


def generate_function_endpoint(name: str, func_id: str) -> str:
    """Generate function endpoint URL"""
    return f"https://fn-{name}-{func_id[:8]}.{settings.BASE_DOMAIN}/invoke"


@router.post("", response_model=FunctionResponse, status_code=status.HTTP_201_CREATED)
async def create_function(
    func_data: FunctionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create serverless function"""
    db = get_database()
    
    # Check if function name exists
    existing = await db.functions.find_one({
        "user_id": current_user["_id"],
        "name": func_data.name
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Function with this name already exists"
        )
    
    # Create function
    function = {
        "_id": secrets.token_urlsafe(16),
        "name": func_data.name,
        "user_id": current_user["_id"],
        "runtime": func_data.runtime.value,
        "code": func_data.code,
        "handler": func_data.handler,
        "env_vars": func_data.env_vars or {},
        "timeout": func_data.timeout,
        "endpoint": "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    function["endpoint"] = generate_function_endpoint(function["name"], function["_id"])
    
    await db.functions.insert_one(function)
    
    logger.info(f"Function created: {function['name']} by user {current_user['email']}")
    
    return FunctionResponse(**function)


@router.get("", response_model=List[FunctionResponse])
async def list_functions(current_user: dict = Depends(get_current_user)):
    """List user's functions"""
    db = get_database()
    
    cursor = db.functions.find({"user_id": current_user["_id"]})
    functions = await cursor.to_list(length=None)
    
    return [FunctionResponse(**func) for func in functions]


@router.get("/{function_id}", response_model=FunctionResponse)
async def get_function(
    function_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get function details"""
    db = get_database()
    
    function = await db.functions.find_one({
        "_id": function_id,
        "user_id": current_user["_id"]
    })
    
    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found"
        )
    
    return FunctionResponse(**function)


@router.patch("/{function_id}", response_model=FunctionResponse)
async def update_function(
    function_id: str,
    func_data: FunctionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update function"""
    db = get_database()
    
    function = await db.functions.find_one({
        "_id": function_id,
        "user_id": current_user["_id"]
    })
    
    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found"
        )
    
    update_data = {"updated_at": datetime.utcnow()}
    if func_data.code is not None:
        update_data["code"] = func_data.code
    if func_data.env_vars is not None:
        update_data["env_vars"] = func_data.env_vars
    if func_data.timeout is not None:
        update_data["timeout"] = func_data.timeout
    
    await db.functions.update_one(
        {"_id": function_id},
        {"$set": update_data}
    )
    
    function = await db.functions.find_one({"_id": function_id})
    
    logger.info(f"Function updated: {function['name']} by user {current_user['email']}")
    
    return FunctionResponse(**function)


@router.delete("/{function_id}")
async def delete_function(
    function_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete function"""
    db = get_database()
    
    function = await db.functions.find_one({
        "_id": function_id,
        "user_id": current_user["_id"]
    })
    
    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found"
        )
    
    await db.functions.delete_one({"_id": function_id})
    
    logger.info(f"Function deleted: {function['name']} by user {current_user['email']}")
    
    return {"message": "Function deleted successfully"}


@router.post("/{function_id}/invoke")
async def invoke_function(
    function_id: str,
    invoke_data: FunctionInvoke,
    current_user: dict = Depends(get_current_user)
):
    """Invoke serverless function"""
    db = get_database()
    
    function = await db.functions.find_one({
        "_id": function_id,
        "user_id": current_user["_id"]
    })
    
    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found"
        )
    
    # Simulate function execution
    result = {
        "function_id": function_id,
        "status": "success",
        "execution_time_ms": 125,
        "output": {
            "message": f"Function {function['name']} executed successfully",
            "payload": invoke_data.payload
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Log execution
    await db.logs.insert_one({
        "_id": secrets.token_urlsafe(16),
        "function_id": function_id,
        "log_type": "function_execution",
        "message": f"Function {function['name']} invoked",
        "level": "info",
        "created_at": datetime.utcnow()
    })
    
    logger.info(f"Function invoked: {function['name']} by user {current_user['email']}")
    
    return result
