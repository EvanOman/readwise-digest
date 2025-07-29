"""Logging configuration for the Readwise Digest SDK."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    log_file: Optional[str] = None,
    include_timestamp: bool = True,
    include_module: bool = True,
) -> None:
    """Set up logging configuration for the SDK.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
        log_file: Optional file path to write logs to
        include_timestamp: Include timestamp in log messages
        include_module: Include module name in log messages
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Default format
    if not format_string:
        format_parts = []
        if include_timestamp:
            format_parts.append("%(asctime)s")
        format_parts.append("%(levelname)s")
        if include_module:
            format_parts.append("%(name)s")
        format_parts.append("%(message)s")
        format_string = " - ".join(format_parts)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[],
    )

    # Get the root logger and clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Create file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set level for our SDK loggers
    logging.getLogger("readwise_digest").setLevel(numeric_level)

    # Reduce noise from HTTP libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the SDK naming convention.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    # Ensure the name starts with our package name
    if not name.startswith("readwise_digest"):
        if name == "__main__":
            name = "readwise_digest.main"
        else:
            name = f"readwise_digest.{name}"

    return logging.getLogger(name)


def setup_from_env() -> None:
    """Set up logging from environment variables.

    Environment variables:
        READWISE_LOG_LEVEL: Logging level (default: INFO)
        READWISE_LOG_FORMAT: Custom format string
        READWISE_LOG_FILE: Path to log file
        READWISE_LOG_TIMESTAMP: Include timestamp (default: true)
        READWISE_LOG_MODULE: Include module name (default: true)
    """
    level = os.getenv("READWISE_LOG_LEVEL", "INFO")
    format_string = os.getenv("READWISE_LOG_FORMAT")
    log_file = os.getenv("READWISE_LOG_FILE")
    include_timestamp = os.getenv("READWISE_LOG_TIMESTAMP", "true").lower() == "true"
    include_module = os.getenv("READWISE_LOG_MODULE", "true").lower() == "true"

    setup_logging(
        level=level,
        format_string=format_string,
        log_file=log_file,
        include_timestamp=include_timestamp,
        include_module=include_module,
    )


class ContextFilter(logging.Filter):
    """Filter to add contextual information to log records."""

    def __init__(self, context: dict):
        super().__init__()
        self.context = context

    def filter(self, record):
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class RequestIdFilter(logging.Filter):
    """Filter to add request IDs to log records."""

    def __init__(self):
        super().__init__()
        self.request_counter = 0

    def filter(self, record):
        if not hasattr(record, "request_id"):
            self.request_counter += 1
            record.request_id = f"req_{self.request_counter:06d}"
        return True


# Default setup from environment if available
if "READWISE_LOG_LEVEL" in os.environ:
    setup_from_env()
