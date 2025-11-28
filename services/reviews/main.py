"""
Reviews Service - Main Application
Smart Meeting Room Management System

This service handles:
- Review creation and management for meeting rooms
- Rating system (1-5 stars) for room quality feedback
- Review moderation (flagging inappropriate content)
- Review filtering by room, user, rating, or flagged status
- Average rating calculations for rooms

Author: Reem Hamdar
Port: 8004
"""
import threading
import time

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from core.rabbitmq_client import logger
from rabbitmq_instance import rabbitmq_client
# Import the router module from the local `router` package
from router.reviews_router import router as reviews_router



app = FastAPI(
    title="Room Reviews Service API",
    description="""
## Smart Meeting Room Reviews & Ratings Service

This service manages reviews and ratings for meeting rooms, providing feedback and quality insights.

### Features
* **Review Management**: Create, update, delete, and retrieve room reviews
* **Rating System**: 1-5 star rating system for room quality
* **Review Moderation**: Flag inappropriate reviews (admin/manager only)
* **Review Filtering**: Filter reviews by room, user, rating, or flagged status
* **Caching**: Redis-based caching for improved query performance

### Authentication
Most endpoints require JWT authentication. Include the token in the `Authorization` header:
```
Authorization: Bearer <your_jwt_token>
```

### Roles & Permissions
- **Admin**: Full access including review moderation and deletion
- **Manager**: Can moderate (flag/unflag) reviews
- **User**: Can create, read, update, and delete their own reviews

### Rating Scale
Reviews use a 1-5 star rating system:
- ⭐ (1): Poor
- ⭐⭐ (2): Fair
- ⭐⭐⭐ (3): Good
- ⭐⭐⭐⭐ (4): Very Good
- ⭐⭐⭐⭐⭐ (5): Excellent

### Error Handling
The API uses standard HTTP status codes and returns structured error responses:
- `200`: Success
- `201`: Created
- `204`: No Content (successful deletion/update)
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `409`: Conflict (e.g., duplicate review)
- `422`: Validation Error
- `500`: Internal Server Error

### Rate Limiting
API responses are cached for 5 minutes (300 seconds) to improve performance.
    """,
    version="1.0.0"
)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions (404, 403, etc.)"""
    logger.error(f"HTTP error occurred: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors (invalid input data)"""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Invalid input data",
            "details": exc.errors(),
            "path": str(request.url)
        }
    )

@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.error(f"Pydantic validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Data Validation Error",
            "message": "Invalid data format",
            "details": exc.errors(),
            "path": str(request.url)
        }
    )

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors (unique constraint violations, etc.)"""
    logger.error(f"Database integrity error: {str(exc.orig)}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "Database Integrity Error",
            "message": "A database constraint was violated (e.g., duplicate entry)",
            "details": str(exc.orig) if hasattr(exc, 'orig') else str(exc),
            "path": str(request.url)
        }
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle general SQLAlchemy database errors"""
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database Error",
            "message": "An error occurred while accessing the database",
            "details": str(exc),
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other unhandled exceptions"""
    logger.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "details": str(exc),
            "type": type(exc).__name__,
            "path": str(request.url)
        }
    )

app.include_router(reviews_router)

@app.get(
    "/",
    tags=["health"],
    summary="Root endpoint"
)
async def root():
    """
    Root endpoint - confirms service is running.
    Returns basic service information and status.
    """
    return {
        "service": "reviews",
        "status": "running",
        "version": "1.0.0"
    }

@app.get(
    "/health",
    tags=["health"],
    summary="Health check endpoint"
)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    Returns service status and availability.
    Used by container orchestration and monitoring tools.
    """
    return {
        "status": "healthy",
        "service": "reviews"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    
    # Start Uvicorn server
    uvicorn.run(
        app,
        host="0.0.0.0",    # Listen on all network interfaces
        port=8004,          # Reviews service port
        reload=False,
        log_level="info"
    )