"""Custom exceptions for the Readwise SDK."""

from typing import Any, Optional


class ReadwiseError(Exception):
    """Base exception for all Readwise API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(ReadwiseError):
    """Raised when API authentication fails."""


class RateLimitError(ReadwiseError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class NotFoundError(ReadwiseError):
    """Raised when a requested resource is not found."""


class ValidationError(ReadwiseError):
    """Raised when request validation fails."""


class ServerError(ReadwiseError):
    """Raised when server returns 5xx errors."""
