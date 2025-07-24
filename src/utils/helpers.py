from dotenv import load_dotenv
import os
from datetime import datetime

def load_env():
    load_dotenv()
    return {
        "CLICKUP_API_KEY": os.getenv("CLICKUP_API_KEY")
    }




def date_to_milliseconds(date_input):
    """
    Converts a date input to a Unix timestamp in milliseconds.
    Accepts:
      - int or str representing milliseconds since epoch
      - ISO 8601 date string (e.g. '2025-05-21T00:00:00')
      - 'YYYY-MM-DD' format
    Returns:
      - Timestamp in milliseconds (int), or None if invalid
    """
    try:
        # If it's already a number (ms timestamp), return as int
        if isinstance(date_input, (int, float)) or (isinstance(date_input, str) and date_input.isdigit()):
            ms = int(date_input)
            return ms if ms > 0 else None

        # Try parsing as ISO 8601 string
        try:
            dt = datetime.fromisoformat(date_input)
        except ValueError:
            # Try 'YYYY-MM-DD'
            dt = datetime.strptime(date_input, "%Y-%m-%d")

        return int(dt.timestamp() * 1000)

    except Exception:
        return None


def to_human_readable_date(ms_timestamp):
    """
    Converts a Unix timestamp in milliseconds to a human-readable date string.
    
    Args:
        ms_timestamp (int or str): Milliseconds since epoch.
    
    Returns:
        str: Date string in 'YYYY-MM-DD HH:MM:SS' format (UTC), or None if invalid.
    """
    try:
        ms = int(ms_timestamp)
        if ms < 0:
            return None
        dt = datetime.utcfromtimestamp(ms / 1000)  # Convert to seconds
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return None