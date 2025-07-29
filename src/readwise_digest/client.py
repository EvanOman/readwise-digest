"""Core API client for Readwise."""

import logging
import os
from collections.abc import Iterator
from datetime import datetime
from typing import Any, Optional, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ReadwiseError,
    ServerError,
    ValidationError,
)
from .models import Book, Highlight, Tag


class ReadwiseClient:
    """Main client for interacting with the Readwise API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://readwise.io/api/v2",
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        timeout: int = 30,
    ):
        self.api_key = api_key or os.getenv("READWISE_API_KEY")
        if not self.api_key:
            raise AuthenticationError("API key is required. Set READWISE_API_KEY environment variable or pass api_key parameter.")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

        # Configure session with retries
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ReadwiseDigest/0.1.0",
        })

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make HTTP request to Readwise API with error handling."""
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    retry_after=retry_after,
                    status_code=response.status_code,
                )

            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Check your API key.",
                    status_code=response.status_code,
                )

            # Handle not found
            if response.status_code == 404:
                raise NotFoundError(
                    "Resource not found.",
                    status_code=response.status_code,
                )

            # Handle validation errors
            if response.status_code == 400:
                raise ValidationError(
                    f"Validation error: {response.text}",
                    status_code=response.status_code,
                    response=response.json() if response.content else None,
                )

            # Handle server errors
            if response.status_code >= 500:
                raise ServerError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                )

            # Raise for other HTTP errors
            response.raise_for_status()

            return response.json() if response.content else {}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise ReadwiseError(f"Request failed: {e}")

    def get_books(
        self,
        page_size: int = 1000,
        category: Optional[str] = None,
        source: Optional[str] = None,
        updated_after: Optional[Union[datetime, str]] = None,
    ) -> Iterator[Book]:
        """Get all books with optional filtering."""
        params = {"page_size": page_size}

        if category:
            params["category"] = category
        if source:
            params["source"] = source
        if updated_after:
            if isinstance(updated_after, datetime):
                params["updated__gt"] = updated_after.isoformat()
            else:
                params["updated__gt"] = updated_after

        next_url = "books/"

        while next_url:
            if next_url.startswith("http"):
                # Handle full URLs from pagination
                response = self.session.get(next_url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
            else:
                data = self._make_request("GET", next_url, params=params)

            for book_data in data.get("results", []):
                yield Book.from_dict(book_data)

            next_url = data.get("next")
            if next_url and next_url.startswith("http"):
                # Extract just the path and query from full URL
                from urllib.parse import urlparse
                parsed = urlparse(next_url)
                # Remove the /api/v2 prefix since _make_request adds it
                path = parsed.path
                path = path.removeprefix("/api/v2/")  # Remove "/api/v2/"
                next_url = path + ("?" + parsed.query if parsed.query else "")

            # Clear params for subsequent requests as they're in the next_url
            params = None

    def get_highlights(
        self,
        page_size: int = 1000,
        book_id: Optional[int] = None,
        updated_after: Optional[Union[datetime, str]] = None,
        highlighted_after: Optional[Union[datetime, str]] = None,
    ) -> Iterator[Highlight]:
        """Get all highlights with optional filtering."""
        params = {"page_size": page_size}

        if book_id:
            params["book_id"] = book_id
        if updated_after:
            if isinstance(updated_after, datetime):
                params["updated__gt"] = updated_after.isoformat()
            else:
                params["updated__gt"] = updated_after
        if highlighted_after:
            if isinstance(highlighted_after, datetime):
                params["highlighted_at__gt"] = highlighted_after.isoformat()
            else:
                params["highlighted_at__gt"] = highlighted_after

        next_url = "highlights/"

        while next_url:
            if next_url.startswith("http"):
                response = self.session.get(next_url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
            else:
                data = self._make_request("GET", next_url, params=params)

            for highlight_data in data.get("results", []):
                yield Highlight.from_dict(highlight_data)

            next_url = data.get("next")
            if next_url and next_url.startswith("http"):
                from urllib.parse import urlparse
                parsed = urlparse(next_url)
                # Remove the /api/v2 prefix since _make_request adds it
                path = parsed.path
                path = path.removeprefix("/api/v2/")  # Remove "/api/v2/"
                next_url = path + ("?" + parsed.query if parsed.query else "")

            params = None

    def get_book(self, book_id: int) -> Book:
        """Get a specific book by ID."""
        data = self._make_request("GET", f"books/{book_id}/")
        return Book.from_dict(data)

    def get_highlight(self, highlight_id: int) -> Highlight:
        """Get a specific highlight by ID."""
        data = self._make_request("GET", f"highlights/{highlight_id}/")
        return Highlight.from_dict(data)

    def create_highlight(
        self,
        text: str,
        title: str,
        author: Optional[str] = None,
        source_url: Optional[str] = None,
        source_type: str = "manual",
        category: str = "articles",
        note: Optional[str] = None,
        highlighted_at: Optional[datetime] = None,
        location_type: str = "manual",
    ) -> Highlight:
        """Create a new highlight."""
        data = {
            "highlights": [{
                "text": text,
                "title": title,
                "author": author,
                "source_url": source_url,
                "source_type": source_type,
                "category": category,
                "note": note,
                "highlighted_at": highlighted_at.isoformat() if highlighted_at else None,
                "location_type": location_type,
            }],
        }

        response = self._make_request("POST", "highlights/", json_data=data)
        # API returns a list, get the first highlight
        highlight_data = response[0] if isinstance(response, list) else response
        return Highlight.from_dict(highlight_data)

    def update_highlight(self, highlight_id: int, **kwargs) -> Highlight:
        """Update an existing highlight."""
        # Filter out None values
        update_data = {k: v for k, v in kwargs.items() if v is not None}

        data = self._make_request("PATCH", f"highlights/{highlight_id}/", json_data=update_data)
        return Highlight.from_dict(data)

    def delete_highlight(self, highlight_id: int) -> None:
        """Delete a highlight."""
        self._make_request("DELETE", f"highlights/{highlight_id}/")

    def get_tags(self) -> list[Tag]:
        """Get all tags."""
        data = self._make_request("GET", "tags/")
        return [Tag.from_dict(tag_data) for tag_data in data.get("results", [])]

    def export_highlights(
        self,
        format: str = "json",
        updated_after: Optional[Union[datetime, str]] = None,
    ) -> str:
        """Export highlights in various formats."""
        params = {"format": format}
        if updated_after:
            if isinstance(updated_after, datetime):
                params["updated__gt"] = updated_after.isoformat()
            else:
                params["updated__gt"] = updated_after

        response = self.session.get(
            urljoin(self.base_url + "/", "export/"),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text

    def close(self):
        """Close the HTTP session."""
        self.session.close()
