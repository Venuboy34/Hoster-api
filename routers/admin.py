"""
Admin router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime

from models import UserResponse, AdminUserUpdate, UsageMetrics, UserRole
from routers.auth import get_admin_user
from database import get_database

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def list_all_users(admin: dict = Depends(get_admin_user)):
    """List all users (admin only)"""
    db = get_database()
    
    cursor = db.users.find({})
    users = await cursor.to_list(length=None)
    
    return [
        UserResponse(
            id=user["_id"],
            username=user["username"],
            email=user["email"],
            role=UserRole(user["role"]),
            created_at=user["created_at"],
            is_active=user["is_active"]
        )
        for user in users
    ]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: str,
    user_data: AdminUserUpdate,
    admin: dict = Depends(get_admin_user)
):
    """Update user (admin only)"""
    db = get_database()
    
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = {}
    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active
    if user_data.role is not None:
        update_data["role"] = user_data.role.value
    
    if update_data:
        await db.users.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )
    
    user = await db.users.find_one({"_id": user_id})
    
    return UserResponse(
        id=user["_id"],
        username=user["username"],
        email=user["email"],
        role=UserRole(user["role"]),
        created_at=user["created_at"],
        is_active=user["is_active"]
    )


@router.get("/stats")
async def get_platform_stats(admin: dict = Depends(get_admin_user)):
    """Get platform statistics (admin only)"""
    db = get_database()
    
    total_users = await db.users.count_documents({})
    total_apps = await db.apps.count_documents({})
    total_deployments = await db.deployments.count_documents({})
    total_functions = await db.functions.count_documents({})
    
    return {
        "total_users": total_users,
        "total_apps": total_apps,
        "total_deployments": total_deployments,
        "total_functions": total_functions,
        "timestamp": datetime.utcnow().isoformat()
    }
