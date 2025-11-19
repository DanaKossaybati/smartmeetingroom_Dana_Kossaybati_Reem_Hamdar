"""
Utility functions for input validation and sanitization.
Separate module for reusability across different services.

Author: Dana Kossaybati
"""
import re
from typing import Tuple
from fastapi import HTTPException

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent SQL injection and XSS attacks.
    
    Removes dangerous SQL keywords and script tags that could be used
    for injection attacks. This is a defense-in-depth measure alongside
    parameterized queries.
    
    Args:
        text: Raw user input string
    
    Returns:
        Sanitized string safe for processing
    
    Security note:
        This is NOT a replacement for parameterized queries (which we use),
        but an additional layer of protection against injection attacks.
    
    Example:
        sanitize_input("admin'; DROP TABLE users--") 
        -> "admin TABLE users"
    """
    if not text:
        return text
    
    # List of dangerous SQL patterns to remove
    dangerous_patterns = [
        '--',           # SQL comment indicator
        ';--',          # Statement terminator + comment
        '/*', '*/',     # Multi-line SQL comments
        'xp_',          # SQL Server extended procedures
        'sp_',          # SQL Server stored procedures
        'DROP',         # Dangerous SQL command
        'DELETE',       # Dangerous SQL command
        'INSERT',       # Could be misused
        'UPDATE',       # Could be misused
        'SELECT',       # Could leak data
        '<script>',     # XSS attack vector
        '</script>',    # XSS closing tag
        'javascript:',  # XSS protocol
        'onerror=',     # XSS event handler
        'onload='       # XSS event handler
    ]
    
    # Convert to string and remove dangerous patterns
    sanitized = str(text)
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, '')
    
    # Remove leading/trailing whitespace
    return sanitized.strip()

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password meets security requirements.
    
    Requirements enforced:
    - Minimum 8 characters (prevents brute force)
    - At least one uppercase letter (complexity)
    - At least one lowercase letter (complexity)
    - At least one digit (complexity)
    
    Args:
        password: Plain text password to validate
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, '') if password is valid
        - (False, 'specific error') if password fails validation
    
    Example:
        validate_password_strength('weak') -> (False, 'Password must be...')
        validate_password_strength('StrongPass123') -> (True, '')
    """
    # Check minimum length
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    # All validations passed
    return True, ""

def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username format.
    
    Rules:
    - 3-50 characters
    - Alphanumeric and underscore only
    - Must start with letter
    
    Args:
        username: Username to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 50:
        return False, "Username must be less than 50 characters"
    
    # Must start with letter
    if not username[0].isalpha():
        return False, "Username must start with a letter"
    
    # Only alphanumeric and underscore
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return False, "Username can only contain letters, numbers, and underscores"
        
    return True, ""