import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

##from consumers.user_events_consumer import start_payment_consumer
##from core.rabbitmq_client import logger
from database import init_db
##from rabbitmq_instance import rabbitmq_client
from router import rooms

@asynccontextmanager
async def lifespan(app: FastAPI):
    #initialize database
    init_db()
    logger.info("Database initialized")
    max_retries = 5
    retry_delay = 2
    # Startup: Connect to RabbitMQ and start consumers

    for attempt in range(max_retries):
        try:
            if rabbitmq_client.connect():
                logger.info("✅ RabbitMQ connected successfully")

                # Start consumer in background thread
                consumer_thread = threading.Thread(
                    target=start_payment_consumer,
                    daemon=True
                )
                consumer_thread.start()
                logger.info("🚀 Payment consumer started in background")
                break
        except Exception as e:
            logger.warning(f"RabbitMQ connection attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("❌ Failed to connect to RabbitMQ after all retries")

    yield

    # Shutdown: Clean up
    ##rabbitmq_client.close()

app = FastAPI(
    title="My FastAPI Application",
    description="This is a sample FastAPI application.",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(rooms.router)