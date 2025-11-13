"""
Apps management router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
import secrets
import logging

from models import (
    AppCreate, AppUpdate, AppResponse, AppStatus,
    DeploymentSource, MessageResponse
)
from routers.auth import get_current_user
from config import settings
from database import get_database

logger = logging.getLogger(__name__)
router = APIRouter()


def generate_app_url(app_name: str, app_id: str) -> str:
    """Generate app URL"""
    return f"https://{app_name}-{app_id[:8]}.{settings.BASE_DOMAIN}"


@router.post("", response_model=AppResponse, status_code=status.HTTP_201_CREATED)
async def create_app(
    app_data: AppCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new app"""
    db = get_database()
    
    # Check app limit
    user_apps_count = await db.apps.count_documents({"user_id": current_user["_id"]})
    if user_apps_count >= settings.MAX_APPS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.MAX_APPS_PER_USER} apps per user"
        )
    
    # Check if app name exists for user
    existing = await db.apps.find_one({
        "user_id": current_user["_id"],
        "name": app_data.name
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="App with this name already exists"
        )
    
    # Validate source config
    if app_data.source_type == DeploymentSource.GITHUB:
        if "repo_url" not in app_data.source_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub repo_url required in source_config"
            )
    elif app_data.source_type == DeploymentSource.DOCKER:
        if "image" not in app_data.source_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Docker image required in source_config"
            )
    
    # Create app
    app = {
        "_id": secrets.token_urlsafe(16),
        "name": app_data.name,
        "description": app_data.description,
        "user_id": current_user["_id"],
        "status": AppStatus.PENDING.value,
        "source_type": app_data.source_type.value,
        "source_config": app_data.source_config,
        "env_vars": app_data.env_vars or {},
        "url": "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    app["url"] = generate_app_url(app["name"], app["_id"])
    
    await db.apps.insert_one(app)
    
    # Create initial deployment log
    await db.logs.insert_one({
        "_id": secrets.token_urlsafe(16),
        "app_id": app["_id"],
        "log_type": "deployment",
        "message": f"App '{app['name']}' created",
        "level": "info",
        "created_at": datetime.utcnow()
    })
    
    logger.info(f"App created: {app['name']} by user {current_user['email']}")
    
    return AppResponse(
        id=app["_id"],
        name=app["name"],
        description=app["description"],
        user_id=app["user_id"],
        status=AppStatus(app["status"]),
        source_type=DeploymentSource(app["source_type"]),
        source_config=app["source_config"],
        env_vars=app["env_vars"],
        url=app["url"],
        created_at=app["created_at"],
        updated_at=app["updated_at"]
    )


@router.get("", response_model=List[AppResponse])
async def list_apps(current_user: dict = Depends(get_current_user)):
    """List user's apps"""
    db = get_database()
    
    cursor = db.apps.find({"user_id": current_user["_id"]})
    apps = await cursor.to_list(length=None)
    
    return [
        AppResponse(
            id=app["_id"],
            name=app["name"],
            description=app.get("description"),
            user_id=app["user_id"],
            status=AppStatus(app["status"]),
            source_type=DeploymentSource(app["source_type"]),
            source_config=app["source_config"],
            env_vars=app.get("env_vars", {}),
            url=app["url"],
            created_at=app["created_at"],
            updated_at=app["updated_at"]
        )
        for app in apps
    ]


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get app details"""
    db = get_database()
    
    app = await db.apps.find_one({
        "_id": app_id,
        "user_id": current_user["_id"]
    })
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    return AppResponse(
        id=app["_id"],
        name=app["name"],
        description=app.get("description"),
        user_id=app["user_id"],
        status=AppStatus(app["status"]),
        source_type=DeploymentSource(app["source_type"]),
        source_config=app["source_config"],
        env_vars=app.get("env_vars", {}),
        url=app["url"],
        created_at=app["created_at"],
        updated_at=app["updated_at"]
    )


@router.patch("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: str,
    app_data: AppUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update app"""
    db = get_database()
    
    app = await db.apps.find_one({
        "_id": app_id,
        "user_id": current_user["_id"]
    })
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    update_data = {}
    if app_data.description is not None:
        update_data["description"] = app_data.description
    if app_data.env_vars is not None:
        update_data["env_vars"] = app_data.env_vars
    if app_data.status is not None:
        update_data["status"] = app_data.status.value
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db.apps.update_one(
        {"_id": app_id},
        {"$set": update_data}
    )
    
    # Get updated app
    app = await db.apps.find_one({"_id": app_id})
    
    logger.info(f"App updated: {app['name']} by user {current_user['email']}")
    
    return AppResponse(
        id=app["_id"],
        name=app["name"],
        description=app.get("description"),
        user_id=app["user_id"],
        status=AppStatus(app["status"]),
        source_type=DeploymentSource(app["source_type"]),
        source_config=app["source_config"],
        env_vars=app.get("env_vars", {}),
        url=app["url"],
        created_at=app["created_at"],
        updated_at=app["updated_at"]
    )


@router.delete("/{app_id}")
async def delete_app(
    app_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete app"""
    db = get_database()
    
    app = await db.apps.find_one({
        "_id": app_id,
        "user_id": current_user["_id"]
    })
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Delete app
    await db.apps.delete_one({"_id": app_id})
    
    # Delete associated deployments and logs
    await db.deployments.delete_many({"app_id": app_id})
    await db.logs.delete_many({"app_id": app_id})
    
    logger.info(f"App deleted: {app['name']} by user {current_user['email']}")
    
    return {"message": "App deleted successfully"}


@router.post("/{app_id}/start", response_model=MessageResponse)
async def start_app(
    app_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Start app"""
    db = get_database()
    
    app = await db.apps.find_one({
        "_id": app_id,
        "user_id": current_user["_id"]
    })
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Update app status
    await db.apps.update_one(
        {"_id": app_id},
        {"$set": {"status": AppStatus.RUNNING.value, "updated_at": datetime.utcnow()}}
    )
    
    # Log action
    await db.logs.insert_one({
        "_id": secrets.token_urlsafe(16),
        "app_id": app_id,
        "log_type": "runtime",
        "message": f"App '{app['name']}' started",
        "level": "info",
        "created_at": datetime.utcnow()
    })
    
    logger.info(f"App started: {app['name']} by user {current_user['email']}")
    
    return MessageResponse(message="App started successfully")


@router.post("/{app_id}/stop", response_model=MessageResponse)
async def stop_app(
    app_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Stop app"""
    db = get_database()
    
    app = await db.apps.find_one({
        "_id": app_id,
        "user_id": current_user["_id"]
    })
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Update app status
    await db.apps.update_one(
        {"_id": app_id},
        {"$set": {"status": AppStatus.STOPPED.value, "updated_at": datetime.utcnow()}}
    )
    
    # Log action
    await db.logs.insert_one({
        "_id": secrets.token_urlsafe(16),
        "app_id": app_id,
        "log_type": "runtime",
        "message": f"App '{app['name']}' stopped",
        "level": "info",
        "created_at": datetime.utcnow()
    })
    
    logger.info(f"App stopped: {app['name']} by user {current_user['email']}")
    
    return MessageResponse(message="App stopped successfully")


@router.post("/{app_id}/restart", response_model=MessageResponse)
async def restart_app(
    app_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Restart app"""
    db = get_database()
    
    app = await db.apps.find_one({
        "_id": app_id,
        "user_id": current_user["_id"]
    })
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Update app status
    await db.apps.update_one(
        {"_id": app_id},
        {"$set": {"status": AppStatus.RUNNING.value, "updated_at": datetime.utcnow()}}
    )
    
    # Log action
    await db.logs.insert_one({
        "_id": secrets.token_urlsafe(16),
        "app_id": app_id,
        "log_type": "runtime",
        "message": f"App '{app['name']}' restarted",
        "level": "info",
        "created_at": datetime.utcnow()
    })
    
    logger.info(f"App restarted: {app['name']} by user {current_user['email']}")
    
    return MessageResponse(message="App restarted successfully")
