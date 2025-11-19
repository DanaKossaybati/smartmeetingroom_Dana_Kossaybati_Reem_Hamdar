"""
Custom error handlers and exceptions for Users Service.
Provides consistent error responses across all endpoints.

Author: Dana Kossaybati
"""
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserNotFoundException(HTTPException):
    """
    Custom exception for when a user is not found.
    Provides consistent 404 responses.
    """
    def __init__(self, username: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )

class DuplicateUserException(HTTPException):
    """
    Custom exception for duplicate username or email.
    Provides consistent 409 Conflict responses.
    """
    def __init__(self, field: str, value: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{field.capitalize()} '{value}' already exists"
        )

class UnauthorizedException(HTTPException):
    """
    Custom exception for unauthorized access attempts.
    Provides consistent 403 Forbidden responses.
    """
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )

async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Global handler for database errors.
    Logs the error and returns a safe message to client.
    
    Args:
        request: FastAPI request object
        exc: SQLAlchemy exception that occurred
    
    Returns:
        JSON response with error details
    """
    # Log the actual error for debugging (don't send to client)
    logger.error(f"Database error: {str(exc)}", exc_info=True)
    
    # Check if it's an integrity constraint violation
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": "Database constraint violation. Possible duplicate entry.",
                "type": "integrity_error"
            }
        )
    
    # Generic database error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "A database error occurred. Please try again later.",
            "type": "database_error"
        }
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """
    Global handler for Pydantic validation errors.
    Formats validation errors in a user-friendly way.
    
    Args:
        request: FastAPI request object
        exc: Pydantic validation exception
    
    Returns:
        JSON response with validation errors
    """
    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )
