import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy_utils import create_database, database_exists

load_dotenv()

db_URL = os.getenv("DATABASE_URL")

engine=create_engine(db_URL,
                     pool_pre_ping=True,
                     pool_size=10,
                     max_overflow=20
                     )
if not database_exists(engine.url):
    create_database(engine.url)
    print("Database created successfully")
else:
    print("Database already exists")
SessionLocal= sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base=declarative_base()

def get_db() ->Generator[Session,None,None]:
    db=  SessionLocal()
    try:
        yield db
    except Exception as e :
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    from models import User, Room, Review
    if os.getenv("DOCKER_ENV") == "true":
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized (Docker mode)")
    else:
        print("Skipping table creation (local development)")