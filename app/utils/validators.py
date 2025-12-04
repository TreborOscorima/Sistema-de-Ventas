"""
Validation utilities for inputs.
"""
import re

def validate_positive_number(value: float | str) -> bool:
    """
    Validate if a number is positive.
    """
    try:
        return float(value) > 0
    except (ValueError, TypeError):
        return False

def validate_non_negative(value: float | str) -> bool:
    """
    Validate if a number is non-negative.
    """
    try:
        return float(value) >= 0
    except (ValueError, TypeError):
        return False

def validate_email(email: str) -> bool:
    """
    Validate email format.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def validate_required(value: str) -> bool:
    """
    Validate if a string is not empty.
    """
    return bool(value and value.strip())
