"""
Users Service - Main Application
Smart Meeting Room Management System

This service handles:
- User registration and authentication
- Profile management
- Role-based access control (RBAC)
- JWT token generation and validation

Author: Dana Kossaybati
Port: 8001
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from routes import router as users_router
from errors import database_exception_handler, validation_exception_handler

# Create FastAPI application instance
app = FastAPI(
    title="Users Service",
    description="Authentication and user management microservice for Smart Meeting Room System",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI at http://localhost:8001/docs
    redoc_url="/redoc"     # ReDoc at http://localhost:8001/redoc
)

# Configure CORS (Cross-Origin Resource Sharing)
# Allows frontend applications to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # In production, specify exact origins
    allow_credentials=True,        # Allow cookies/authorization headers
    allow_methods=["*"],           # Allow all HTTP methods
    allow_headers=["*"],           # Allow all headers
)

# Register global exception handlers
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)

# Include API routes
app.include_router(users_router)

@app.get(
    "/",
    tags=["health"],
    summary="Root endpoint"
)
async def root():
    """
    Root endpoint - confirms service is running.
    """
    return {
        "service": "users",
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
    """
    return {
        "status": "healthy",
        "service": "users"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    
    # Start Uvicorn server
    uvicorn.run(
        app,
        host="0.0.0.0",    # Listen on all network interfaces
        port=8001,          # Users service port
        reload=False         
    )