"""Readwise Digest - A comprehensive Python SDK for the Readwise API."""

from .client import ReadwiseClient
from .digest import DigestService
from .exceptions import AuthenticationError, RateLimitError, ReadwiseError
from .logging_config import get_logger, setup_logging
from .models import Book, Highlight, Tag
from .poller import HighlightPoller, PollingConfig

__version__ = "0.1.0"
__author__ = "Readwise Digest"

__all__ = [
    "AuthenticationError",
    "Book",
    "DigestService",
    "Highlight",
    "HighlightPoller",
    "PollingConfig",
    "RateLimitError",
    "ReadwiseClient",
    "ReadwiseError",
    "Tag",
    "get_logger",
    "setup_logging",
]
