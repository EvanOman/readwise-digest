"""Utility functions for the Readwise Digest SDK."""

import os
import json
import time
import functools
from typing import Any, Dict, Optional, Callable, TypeVar, Union
from datetime import datetime, timedelta
from pathlib import Path

F = TypeVar('F', bound=Callable[..., Any])


def load_env_file(env_file: str = ".env") -> Dict[str, str]:
    """Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file
        
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    env_path = Path(env_file)
    
    if not env_path.exists():
        return env_vars
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    env_vars[key.strip()] = value
                    # Also set in os.environ if not already set
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value
    except Exception as e:
        print(f"Warning: Could not load .env file {env_file}: {e}")
    
    return env_vars


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    backoff_max: float = 60.0,
    exceptions: tuple = (Exception,)
) -> Callable[[F], F]:
    """Decorator to retry function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for backoff delay
        backoff_max: Maximum backoff delay in seconds
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    delay = min(backoff_factor * (2 ** attempt), backoff_max)
                    time.sleep(delay)
            
            # Re-raise the last exception
            raise last_exception
        
        return wrapper  # type: ignore
    return decorator


def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely parse JSON string, returning default on error.
    
    Args:
        data: JSON string to parse
        default: Default value to return on parse error
        
    Returns:
        Parsed JSON data or default value
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """Safely serialize data to JSON string, returning default on error.
    
    Args:
        data: Data to serialize
        default: Default string to return on serialization error
        
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default


def parse_datetime_string(date_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime string in various formats.
    
    Args:
        date_str: Datetime string to parse
        
    Returns:
        Parsed datetime object or None
    """
    if not date_str:
        return None
    
    # Common datetime formats to try
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO with microseconds and Z
        "%Y-%m-%dT%H:%M:%SZ",     # ISO with Z
        "%Y-%m-%dT%H:%M:%S.%f",   # ISO with microseconds
        "%Y-%m-%dT%H:%M:%S",      # ISO basic
        "%Y-%m-%d %H:%M:%S",      # Space separated
        "%Y-%m-%d",               # Date only
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try ISO format parsing as fallback
    try:
        # Handle timezone-aware strings
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def format_datetime(dt: datetime, include_microseconds: bool = False) -> str:
    """Format datetime object to ISO string.
    
    Args:
        dt: Datetime object to format
        include_microseconds: Include microseconds in output
        
    Returns:
        ISO formatted datetime string
    """
    if include_microseconds:
        return dt.isoformat()
    else:
        return dt.replace(microsecond=0).isoformat()


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, creating if necessary.
    
    Args:
        path: Directory path to ensure
        
    Returns:
        Path object for the directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to maximum length with suffix.
    
    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append when truncating
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """Sanitize filename by replacing invalid characters.
    
    Args:
        filename: Original filename
        replacement: Character to replace invalid characters with
        
    Returns:
        Sanitized filename
    """
    import re
    
    # Characters that are invalid in filenames on most systems
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    
    # Replace invalid characters
    sanitized = re.sub(invalid_chars, replacement, filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized


def calculate_rate_limit_delay(response_headers: Dict[str, str]) -> Optional[float]:
    """Calculate delay needed for rate limiting based on response headers.
    
    Args:
        response_headers: HTTP response headers
        
    Returns:
        Delay in seconds or None if no rate limiting detected
    """
    # Check for Retry-After header
    retry_after = response_headers.get('Retry-After')
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            # Might be HTTP date format
            try:
                from email.utils import parsedate_to_datetime
                retry_time = parsedate_to_datetime(retry_after)
                return max(0, (retry_time - datetime.now()).total_seconds())
            except Exception:
                pass
    
    # Check for X-RateLimit headers
    remaining = response_headers.get('X-RateLimit-Remaining')
    reset_time = response_headers.get('X-RateLimit-Reset')
    
    if remaining == '0' and reset_time:
        try:
            reset_timestamp = int(reset_time)
            current_time = int(time.time())
            return max(0, reset_timestamp - current_time)
        except ValueError:
            pass
    
    return None


def batch_items(items: list, batch_size: int):
    """Yield successive batches from a list.
    
    Args:
        items: List of items to batch
        batch_size: Size of each batch
        
    Yields:
        Batches of items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def measure_execution_time(func: F) -> F:
    """Decorator to measure and log function execution time.
    
    Args:
        func: Function to measure
        
    Returns:
        Decorated function that logs execution time
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import logging
        
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper  # type: ignore


def get_user_agent() -> str:
    """Get user agent string for API requests.
    
    Returns:
        User agent string
    """
    from . import __version__
    import platform
    
    python_version = f"{platform.python_version()}"
    system = f"{platform.system()} {platform.release()}"
    
    return f"ReadwiseDigest/{__version__} (Python {python_version}; {system})"


def validate_api_key(api_key: str) -> bool:
    """Validate API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if API key format is valid
    """
    if not api_key or not isinstance(api_key, str):
        return False
    
    # Basic validation - should be a non-empty string
    # Readwise API keys are typically long alphanumeric strings
    return len(api_key.strip()) > 10 and api_key.isalnum()


# Initialize environment on import
load_env_file()