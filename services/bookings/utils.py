"""
Utility functions for Bookings Service.
Reusable validation, caching and helper functions.

Author: Dana Kossaybati
"""
from datetime import datetime, date as date_type, time as time_type
from typing import Tuple
from redis import Redis
import json
from functools import wraps

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent SQL injection and XSS attacks.
    
    Removes dangerous SQL keywords and script tags.
    This is defense-in-depth alongside parameterized queries.
    
    Args:
        text: Raw user input string
    
    Returns:
        Sanitized string safe for processing
    """
    if not text:
        return text
    
    # List of dangerous patterns to remove
    dangerous_patterns = [
        '--', ';--', '/*', '*/',
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT',
        '<script>', '</script>', 'javascript:', 'onerror='
    ]
    
    sanitized = str(text)
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, '')
    
    return sanitized.strip()

def validate_booking_time(
    booking_date: date_type,
    start_time: time_type,
    end_time: time_type
) -> Tuple[bool, str]:
    """
    Validate booking date and time constraints.
    
    Business rules:
    - Cannot book dates in the past
    - End time must be after start time
    - Booking duration must be reasonable (not too short/long)
    
    Args:
        booking_date: Date of booking
        start_time: Start time
        end_time: End time
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if date is in the past
    today = datetime.now().date()
    if booking_date < today:
        return False, "Cannot book dates in the past"
    
    # Check time order (redundant with Pydantic but good for service layer)
    if start_time >= end_time:
        return False, "End time must be after start time"
    
    # Check minimum duration (15 minutes)
    # Convert times to datetime for calculation
    start_dt = datetime.combine(booking_date, start_time)
    end_dt = datetime.combine(booking_date, end_time)
    duration = (end_dt - start_dt).total_seconds() / 60  # minutes
    
    if duration < 15:
        return False, "Booking duration must be at least 15 minutes"
    
    # Check maximum duration (12 hours)
    if duration > 720:
        return False, "Booking duration cannot exceed 12 hours"
    
    return True, ""

def times_overlap(
    start1: time_type,
    end1: time_type,
    start2: time_type,
    end2: time_type
) -> bool:
    """
    Check if two time ranges overlap.
    
    Used for conflict detection between bookings.
    Two ranges overlap if one starts before the other ends.
    
    Args:
        start1: Start time of first booking
        end1: End time of first booking
        start2: Start time of second booking
        end2: End time of second booking
    
    Returns:
        True if time ranges overlap, False otherwise
    
    Examples:
        times_overlap(09:00, 10:00, 09:30, 10:30) -> True  (overlap 30 min)
        times_overlap(09:00, 10:00, 10:00, 11:00) -> False (adjacent, no overlap)
        times_overlap(09:00, 10:00, 08:00, 11:00) -> True  (first contained in second)
    """
    # Overlap occurs if start1 < end2 AND start2 < end1
    return start1 < end2 and start2 < end1

# Initialize Redis
try:
    redis_client = Redis(host='localhost', port=6379, decode_responses=True, socket_connect_timeout=2)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    print("Redis not available - running without cache")


def cache_response(expire_seconds=300):
    """
    Cache API responses in Redis to improve performance.

    Wraps an async endpoint function, stores its return value in Redis,
    and automatically returns cached results for identical calls until
    the expiration time is reached.

    Args:
        expire_seconds: How long the cached value should live in Redis.

    Returns:
        A wrapped function that returns either the cached response
        or the fresh response from the original function.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not REDIS_AVAILABLE:
                return await func(*args, **kwargs)
            
            # Create cache key from function name and args
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                print(f"CACHE HIT: {cache_key}")
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            redis_client.setex(cache_key, expire_seconds, json.dumps(result))
            print(f"CACHE MISS: {cache_key}")
            
            return result
        return wrapper
    return decorator
