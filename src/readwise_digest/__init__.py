"""Readwise Digest - A comprehensive Python SDK for the Readwise API."""

from .client import ReadwiseClient
from .models import Highlight, Book, Tag
from .exceptions import ReadwiseError, AuthenticationError, RateLimitError
from .digest import DigestService
from .poller import HighlightPoller, PollingConfig
from .logging_config import setup_logging, get_logger

__version__ = "0.1.0"
__author__ = "Readwise Digest"

__all__ = [
    "ReadwiseClient",
    "Highlight",
    "Book",
    "Tag",
    "ReadwiseError",
    "AuthenticationError",
    "RateLimitError",
    "DigestService",
    "HighlightPoller",
    "PollingConfig",
    "setup_logging",
    "get_logger",
]