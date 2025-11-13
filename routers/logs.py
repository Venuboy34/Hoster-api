"""
Logs router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from models import LogResponse
from routers.auth import get_current_user
from database import get_database

router = APIRouter()


@router.get("", response_model=List[LogResponse])
async def get_logs(
    app_id: Optional[str] = None,
    deployment_id: Optional[str] = None,
    function_id: Optional[str] = None,
    log_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """Get logs"""
    db = get_database()
    
    # Build query
    query = {}
    
    if app_id:
        # Verify app ownership
        app = await db.apps.find_one({
            "_id": app_id,
            "user_id": current_user["_id"]
        })
        if not app:
            raise HTTPException(status_code=404, detail="App not found")
        query["app_id"] = app_id
    
    if deployment_id:
        query["deployment_id"] = deployment_id
    
    if function_id:
        query["function_id"] = function_id
    
    if log_type:
        query["log_type"] = log_type
    
    # If no specific filter, get all logs for user's resources
    if not any([app_id, deployment_id, function_id]):
        user_apps = await db.apps.find({"user_id": current_user["_id"]}).to_list(None)
        app_ids = [app["_id"] for app in user_apps]
        query["app_id"] = {"$in": app_ids}
    
    cursor = db.logs.find(query).sort("created_at", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    
    return [LogResponse(**log) for log in logs]
