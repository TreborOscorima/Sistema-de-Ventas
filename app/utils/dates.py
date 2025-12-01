"""
Date and time utilities.

Pure functions for date/time operations extracted for reusability.
"""
import datetime
import logging


def get_current_timestamp() -> str:
    """
    Get the current timestamp in YYYY-MM-DD HH:MM:SS format.
    
    Returns:
        Current timestamp string
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_today_str() -> str:
    """
    Get today's date in YYYY-MM-DD format.
    
    Returns:
        Today's date string
    """
    return datetime.date.today().strftime("%Y-%m-%d")


def get_current_month_str() -> str:
    """
    Get the current month in YYYY-MM format.
    
    Returns:
        Current month string
    """
    return datetime.date.today().strftime("%Y-%m")


def get_current_week_str() -> str:
    """
    Get the current ISO week in YYYY-WNN format.
    
    Returns:
        Current week string (e.g., "2024-W52")
    """
    return datetime.date.today().strftime("%G-W%V")


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime.datetime | None:
    """
    Safely parse a date string.
    
    Args:
        date_str: The date string to parse
        fmt: The format string (default: "%Y-%m-%d")
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str, fmt)
    except ValueError as e:
        logging.debug(f"Failed to parse date '{date_str}' with format '{fmt}': {e}")
        return None


def format_datetime_display(dt: datetime.datetime | None) -> str:
    """
    Format a datetime for display.
    
    Args:
        dt: The datetime to format
        
    Returns:
        Formatted string or empty string if dt is None
    """
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def parse_date_from_timestamp(timestamp: str) -> datetime.date | None:
    """
    Extract date from a timestamp string (splits on space).
    
    Args:
        timestamp: Timestamp string like "2024-01-15 14:30:00"
        
    Returns:
        Date object or None if parsing fails
    """
    if not timestamp:
        return None
    try:
        date_part = timestamp.split(" ")[0]
        return datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None
