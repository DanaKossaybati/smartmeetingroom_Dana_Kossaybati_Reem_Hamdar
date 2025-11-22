"""
Database connection configuration for Bookings Service.
Handles SQLAlchemy engine creation and session management.

Author: Dana Kossaybati
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment (never hardcode credentials!)
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
# This manages the connection pool to PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,         # Maximum number of connections to maintain
    max_overflow=10      # Maximum overflow connections allowed
)

# Create session factory
# Sessions handle individual database transactions
SessionLocal = sessionmaker(
    autocommit=False,    # Require explicit commit (safer)
    autoflush=False,     # Don't automatically flush changes
    bind=engine          # Bind to our PostgreSQL engine
)

# Base class for all database models
# All SQLAlchemy models will inherit from this
Base = declarative_base()

def get_db():
    """
    Dependency function for FastAPI routes.
    Creates a new database session for each request.
    Automatically closes the session when request completes.
    
    Usage:
        @app.get('/bookings')
        def get_bookings(db: Session = Depends(get_db)):
            return db.query(Booking).all()
    """
    db = SessionLocal()
    try:
        yield db  # Provide database session to the route
    finally:
        db.close()  # Always close session (even if error occurs)
