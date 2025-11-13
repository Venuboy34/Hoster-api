"""
MongoDB database connection and utilities
"""
from motor.motor_asyncio import AsyncIOMotorClient
# Import necessary motor/pymongo errors for robust exception handling
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
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
    
    # 1. Check for critical setting before trying to connect
    if not hasattr(settings, 'MONGODB_URL') or not settings.MONGODB_URL:
        logger.error("FATAL: MONGODB_URL setting is missing or empty. Cannot initialize database.")
        # Re-raise a runtime error to stop the application gracefully
        raise RuntimeError("Missing MONGODB_URL configuration.")


    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000 # Increased timeout for slow connections
        )
        
        # Test connection - This is the line that was crashing the app
        await client.admin.command('ping')
        
        db = client[settings.DATABASE_NAME]
        
        # Create indexes
        await create_indexes()
        
        logger.info(f"Connected to MongoDB: {settings.DATABASE_NAME}")
        
    # Catch any connection-related failures without re-raising to allow the server to fully start 
    # and provide better diagnostics, *if* the database is not strictly required for startup.
    # NOTE: Since the DB is required, we should exit gracefully instead of crashing.
    except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
        logger.error(f"CRITICAL ERROR: Failed to connect or ping MongoDB. Check network or MONGODB_URL. Details: {e}")
        # Re-raise the error as a standard Runtime Error to stop the lifespan and exit the container
        # This prevents the "Upstream Connect Error" by exiting cleanly instead of crashing the process
        raise RuntimeError(f"Database initialization failed: {e}")


async def close_db():
    """Close database connection"""
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")


async def create_indexes():
    """Create database indexes"""
    
    # Check if a database connection exists before attempting index creation
    if not db:
        logger.warning("Skipping index creation: Database connection failed during startup.")
        return

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
    # Safely get LOGS_RETENTION_DAYS, assuming 30 days default if missing
    logs_retention_days = getattr(settings, 'LOGS_RETENTION_DAYS', 30)
    await db.logs.create_index("app_id")
    await db.logs.create_index("deployment_id")
    await db.logs.create_index("created_at", expireAfterSeconds=logs_retention_days * 86400)
    
    # Usage metrics indexes
    await db.usage_metrics.create_index("user_id")
    await db.usage_metrics.create_index("created_at")
    
    logger.info("Database indexes created")


def get_database():
    """Get database instance"""
    return db
