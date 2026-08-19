#!/usr/bin/env python3
"""
Timezone utility functions for consistent datetime handling
"""

from datetime import datetime, timezone
from typing import Optional

def get_utc_now() -> datetime:
    """Get current UTC time with timezone info"""
    return datetime.now(timezone.utc)

def format_datetime_for_api(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime for API response with proper timezone handling"""
    if dt is None:
        return None
    
    # Ensure the datetime is timezone-aware
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Return ISO format with timezone info
    return dt.isoformat()

def parse_datetime_from_api(dt_string: str) -> datetime:
    """Parse datetime string from API with timezone handling"""
    if not dt_string:
        raise ValueError("Empty datetime string")
    
    # Try to parse ISO format
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt
    except ValueError:
        # Fallback to basic parsing
        try:
            dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"Unable to parse datetime string: {dt_string}")

def calculate_next_sync_time_from_interval(last_sync: datetime, interval_minutes: int) -> datetime:
    """Calculate next sync time based on last sync and interval (legacy function)"""
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    
    from datetime import timedelta
    return last_sync + timedelta(minutes=interval_minutes)

def calculate_next_sync_time_from_daily_time(sync_time_str: str, last_sync: datetime = None, sync_date_str: str = None) -> datetime:
    """Calculate next sync time based on daily sync time (HH:MM format) and optional date (YYYY-MM-DD format)"""
    from datetime import date, time as dt_time, timedelta
    
    # Parse sync time (HH:MM format)
    try:
        hour, minute = map(int, sync_time_str.split(':'))
        sync_time = dt_time(hour, minute)
    except (ValueError, AttributeError):
        # Default to 9:00 AM if invalid time
        sync_time = dt_time(9, 0)
    
    now = get_utc_now()
    
    # If a specific date is provided, use that date
    if sync_date_str:
        try:
            sync_date = datetime.strptime(sync_date_str, '%Y-%m-%d').date()
            sync_datetime = datetime.combine(sync_date, sync_time).replace(tzinfo=timezone.utc)
            
            # If the specified date/time has passed, return None (no future sync)
            if sync_datetime <= now:
                return None
            
            return sync_datetime
        except ValueError:
            # Invalid date format, fall back to daily scheduling
            pass
    
    # Daily scheduling logic (no specific date)
    today = now.date()
    
    # Create datetime for today at sync time
    today_sync = datetime.combine(today, sync_time).replace(tzinfo=timezone.utc)
    
    # If we have a last sync, use it to determine the next sync
    if last_sync:
        if last_sync.tzinfo is None:
            last_sync = last_sync.replace(tzinfo=timezone.utc)
        
        last_sync_date = last_sync.date()
        
        # If last sync was today and sync time hasn't passed yet, schedule for today
        if last_sync_date == today and today_sync > now:
            return today_sync
        # If last sync was today and sync time has passed, schedule for tomorrow
        elif last_sync_date == today and today_sync <= now:
            tomorrow = today + timedelta(days=1)
            return datetime.combine(tomorrow, sync_time).replace(tzinfo=timezone.utc)
        # If last sync was before today, schedule for today if time hasn't passed, otherwise tomorrow
        elif last_sync_date < today:
            if today_sync > now:
                return today_sync
            else:
                tomorrow = today + timedelta(days=1)
                return datetime.combine(tomorrow, sync_time).replace(tzinfo=timezone.utc)
        # If last sync was in the future (shouldn't happen), schedule for tomorrow
        else:
            tomorrow = today + timedelta(days=1)
            return datetime.combine(tomorrow, sync_time).replace(tzinfo=timezone.utc)
    
    # No last sync - schedule for today if time hasn't passed, otherwise tomorrow
    if today_sync > now:
        return today_sync
    else:
        tomorrow = today + timedelta(days=1)
        return datetime.combine(tomorrow, sync_time).replace(tzinfo=timezone.utc)

def calculate_next_sync_time(last_sync: datetime, interval_minutes: int = None, sync_time_str: str = None, sync_date_str: str = None) -> datetime:
    """Calculate next sync time - supports both interval and time-based sync"""
    if sync_time_str:
        return calculate_next_sync_time_from_daily_time(sync_time_str, last_sync, sync_date_str)
    elif interval_minutes:
        return calculate_next_sync_time_from_interval(last_sync, interval_minutes)
    else:
        # Default to 9:00 AM if no parameters provided
        return calculate_next_sync_time_from_daily_time('09:00', last_sync, sync_date_str)
