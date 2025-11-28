"""
Database configuration and session management for Reviews Service.
Handles PostgreSQL connection, session lifecycle, and declarative base.

Author: Reem Hamdar
"""
import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy_utils import create_database, database_exists

load_dotenv()

# Database connection URL from environment variables
db_URL = os.getenv("DATABASE_URL")

# Create database engine with connection pooling
# pool_pre_ping: Verify connections before using them
# pool_size: Number of connections to maintain in the pool
# max_overflow: Maximum connections beyond pool_size
engine=create_engine(db_URL,
                     pool_pre_ping=True,
                     pool_size=10,
                     max_overflow=20
                     )

# Create database if it doesn't exist
if not database_exists(engine.url):
    create_database(engine.url)
    print("Database created successfully")
else:
    print("Database already exists")

# Session factory for creating database sessions
SessionLocal= sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base=declarative_base()

def get_db() ->Generator[Session,None,None]:
    """
    Database session dependency for FastAPI.
    
    Provides a database session that:
    - Automatically commits on success
    - Rolls back on exceptions
    - Always closes the connection
    
    Usage:
        @router.get("/reviews")
        def get_reviews(db: Session = Depends(get_db)):
            return db.query(Review).all()
    
    Yields:
        Session: SQLAlchemy database session
    
    Raises:
        Exception: Any database errors are rolled back and re-raised
    """
    db=  SessionLocal()
    try:
        yield db
    except Exception as e :
        db.rollback()
        raise
    finally:
        db.close()

