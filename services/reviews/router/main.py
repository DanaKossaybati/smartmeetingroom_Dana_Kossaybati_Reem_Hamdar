import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.rabbitmq_client import logger
from database import init_db
from rabbitmq_instance import rabbitmq_client
# Import the router module from the local `router` package
from router.rooms_router import router as rooms_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    #initialize database
    init_db()
    logger.info("Database initialized")

app = FastAPI(
    title="My FastAPI Application",
    description="This is a sample FastAPI application.",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(rooms_router)