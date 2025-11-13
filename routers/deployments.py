"""
Deployments management router
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List
from datetime import datetime
import secrets
import logging

from models import DeploymentCreate, DeploymentResponse, AppStatus
from routers.auth import get_current_user
from database import get_database

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_deployment(deployment_id: str, app_id: str):
    """Background task to process deployment"""
    db = get_database()
    
    try:
        # Simulate deployment process
        await db.deployments.update_one(
            {"_id": deployment_id},
            {"$set": {"status": AppStatus.DEPLOYING.value}}
        )
        
        # Add deployment logs
        logs = [
            "Pulling source code...",
            "Building application...",
            "Running tests...",
            "Deploying to server...",
            "Deployment completed successfully"
        ]
        
        await db.deployments.update_one(
            {"_id": deployment_id},
            {"$set": {"logs": logs}}
        )
        
        # Update deployment and app status
        await db.deployments.update_one(
            {"_id": deployment_id},
            {
                "$set": {
                    "status": AppStatus.RUNNING.value,
                    "completed_at": datetime.utcnow()
                }
            }
        )
        
        await db.apps.update_one(
            {"_id": app_id},
            {"$set": {"status": AppStatus.RUNNING.value}}
        )
        
        logger.info(f"Deployment {deployment_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Deployment {deployment_id} failed: {str(e)}")
        await db.deployments.update_one(
            {"_id": deployment_id},
            {
                "$set": {
                    "status": AppStatus.FAILED.value,
                    "completed_at": datetime.utcnow()
                },
                "$push": {"logs": f"Error: {str(e)}"}
            }
        )
        
        await db.apps.update_one(
            {"_id": app_id},
            {"$set": {"status": AppStatus.FAILED.value}}
        )


@router.post("", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment_data: DeploymentCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create new deployment"""
    db = get_database()
    
    # Verify app ownership
    app = await db.apps.find_one({
        "_id": deployment_data.app_id,
        "user_id": current_user["_id"]
    })
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Create deployment
    deployment = {
        "_id": secrets.token_urlsafe(16),
        "app_id": deployment_data.app_id,
        "user_id": current_user["_id"],
        "status": AppStatus.PENDING.value,
        "commit_sha": deployment_data.commit_sha,
        "docker_image": deployment_data.docker_image,
        "logs": ["Deployment initiated"],
        "created_at": datetime.utcnow(),
        "completed_at": None
    }
    
    await db.deployments.insert_one(deployment)
    
    # Start deployment in background
    background_tasks.add_task(process_deployment, deployment["_id"], app["_id"])
    
    logger.info(f"Deployment created: {deployment['_id']} for app {app['name']}")
    
    return DeploymentResponse(**deployment)


@router.get("", response_model=List[DeploymentResponse])
async def list_deployments(
    app_id: str = None,
    current_user: dict = Depends(get_current_user)
):
    """List deployments"""
    db = get_database()
    
    query = {"user_id": current_user["_id"]}
    if app_id:
        query["app_id"] = app_id
    
    cursor = db.deployments.find(query).sort("created_at", -1)
    deployments = await cursor.to_list(length=50)
    
    return [DeploymentResponse(**deployment) for deployment in deployments]


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get deployment details"""
    db = get_database()
    
    deployment = await db.deployments.find_one({
        "_id": deployment_id,
        "user_id": current_user["_id"]
    })
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    return DeploymentResponse(**deployment)
