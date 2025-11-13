"""
MongoDB database connection and utilities
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from typing import Optional
import logging

from config import settings

logger = logging.getLogger(__name__)

# Global database client
client: Optional[AsyncIOMotorClient] = None
db = None


async def init_db():
    """Initialize database connection"""
    global client, db
    
    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        await client.admin.command('ping')
        
        db = client[settings.DATABASE_NAME]
        
        # Create indexes
        await create_indexes()
        
        logger.info(f"Connected to MongoDB: {settings.DATABASE_NAME}")
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_db():
    """Close database connection"""
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")


async def create_indexes():
    """Create database indexes"""
    
    # Users collection indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("api_keys.key", sparse=True)
    
    # Apps collection indexes
    await db.apps.create_index("user_id")
    await db.apps.create_index("name")
    await db.apps.create_index([("user_id", 1), ("name", 1)], unique=True)
    
    # Deployments collection indexes
    await db.deployments.create_index("app_id")
    await db.deployments.create_index("user_id")
    await db.deployments.create_index("status")
    await db.deployments.create_index("created_at")
    
    # Functions collection indexes
    await db.functions.create_index("user_id")
    await db.functions.create_index("name")
    await db.functions.create_index([("user_id", 1), ("name", 1)], unique=True)
    
    # Logs collection indexes
    await db.logs.create_index("app_id")
    await db.logs.create_index("deployment_id")
    await db.logs.create_index("created_at", expireAfterSeconds=settings.LOGS_RETENTION_DAYS * 86400)
    
    # Usage metrics indexes
    await db.usage_metrics.create_index("user_id")
    await db.usage_metrics.create_index("created_at")
    
    logger.info("Database indexes created")


def get_database():
    """Get database instance"""
    return db
