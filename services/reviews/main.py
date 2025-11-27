import threading
import time

from fastapi import FastAPI

from core.rabbitmq_client import logger
from database import init_db
from rabbitmq_instance import rabbitmq_client
# Import the router module from the local `router` package
from router.reviews_router import router as reviews_router

async def lifespan(app: FastAPI):
    # Startup: initialize database
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown: cleanup code goes here if needed
    
app = FastAPI(
    title="My FastAPI Application",
    description="This is a sample FastAPI application.",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(reviews_router)