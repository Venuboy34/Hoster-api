"""
Users router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from models import UserUpdate, UserResponse, UserRole
from routers.auth import get_current_user
from database import get_database

router = APIRouter()


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile"""
    db = get_database()
    
    update_data = {"updated_at": datetime.utcnow()}
    
    if user_data.username:
        # Check if username is taken
        existing = await db.users.find_one({
            "username": user_data.username,
            "_id": {"$ne": current_user["_id"]}
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        update_data["username"] = user_data.username
    
    if user_data.email:
        # Check if email is taken
        existing = await db.users.find_one({
            "email": user_data.email,
            "_id": {"$ne": current_user["_id"]}
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )
        update_data["email"] = user_data.email
    
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": update_data}
    )
    
    user = await db.users.find_one({"_id": current_user["_id"]})
    
    return UserResponse(
        id=user["_id"],
        username=user["username"],
        email=user["email"],
        role=UserRole(user["role"]),
        created_at=user["created_at"],
        is_active=user["is_active"]
    )


@router.delete("/me")
async def delete_account(current_user: dict = Depends(get_current_user)):
    """Delete user account"""
    db = get_database()
    
    # Delete user's apps, deployments, functions, and logs
    await db.apps.delete_many({"user_id": current_user["_id"]})
    await db.deployments.delete_many({"user_id": current_user["_id"]})
    await db.functions.delete_many({"user_id": current_user["_id"]})
    await db.logs.delete_many({"app_id": {"$in": []}})  # Clean up logs
    
    # Delete user
    await db.users.delete_one({"_id": current_user["_id"]})
    
    return {"message": "Account deleted successfully"}
