"""Web interface for Readwise Digest."""

from .app import create_app
from .api import router as api_router

__all__ = ["create_app", "api_router"]