"""
Main FastAPI application for Bookings Service.
Configures the app, middleware, and registers routes.

Author: Dana Kosssaybati
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from routes import router as bookings_router

# Create FastAPI application instance
app = FastAPI(
    title="Bookings Service",
    description="Room reservation and availability management microservice for Smart Meeting Room System",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI at /docs
    redoc_url="/redoc"     # ReDoc at /redoc
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

# Include API routes
app.include_router(bookings_router)

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
        "service": "bookings",
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
        "service": "bookings"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    
    # Start Uvicorn server
    uvicorn.run(
        app,
        host="0.0.0.0",    # Listen on all network interfaces
        port=8003,          # Bookings service port
        reload=True         # Auto-reload on code changes (development only)
    )
