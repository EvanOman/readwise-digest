"""Pytest configuration and fixtures."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.readwise_digest import ReadwiseClient
from src.readwise_digest.models import Book, Highlight, Tag


@pytest.fixture
def mock_client():
    """Create a mock ReadwiseClient."""
    return Mock(spec=ReadwiseClient)


@pytest.fixture
def sample_book():
    """Create a sample Book instance."""
    return Book(
        id=1,
        title="Test Book",
        author="Test Author",
        category="books",
        source="kindle",
        num_highlights=5,
        updated=datetime(2023, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_tag():
    """Create a sample Tag instance."""
    return Tag(id=1, name="important")


@pytest.fixture
def sample_highlight(sample_book, sample_tag):
    """Create a sample Highlight instance."""
    return Highlight(
        id=1,
        text="This is a test highlight",
        note="This is a test note",
        location=42,
        highlighted_at=datetime(2023, 1, 1, 12, 0, 0),
        updated=datetime(2023, 1, 1, 12, 0, 0),
        book_id=1,
        url="https://example.com/highlight",
        color="yellow",
        tags=[sample_tag],
        book=sample_book,
    )


@pytest.fixture
def sample_highlights(sample_book):
    """Create a list of sample Highlight instances."""
    return [
        Highlight(
            id=1,
            text="First highlight",
            note="First note",
            highlighted_at=datetime(2023, 1, 1, 12, 0, 0),
            book_id=1,
            book=sample_book,
        ),
        Highlight(
            id=2,
            text="Second highlight",
            highlighted_at=datetime(2023, 1, 2, 12, 0, 0),
            book_id=1,
            book=sample_book,
        ),
        Highlight(
            id=3,
            text="Third highlight",
            note="Third note",
            highlighted_at=datetime(2023, 1, 3, 12, 0, 0),
            book_id=1,
            book=sample_book,
        ),
    ]


@pytest.fixture
def api_response_highlights():
    """Sample API response for highlights endpoint."""
    return {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": 1,
                "text": "Test highlight 1",
                "note": "Test note 1",
                "location": 42,
                "location_type": "kindle",
                "highlighted_at": "2023-01-01T12:00:00Z",
                "updated": "2023-01-01T12:00:00Z",
                "book_id": 1,
                "url": "https://example.com/1",
                "color": "yellow",
                "tags": [],
                "book": {
                    "id": 1,
                    "title": "Test Book",
                    "author": "Test Author",
                    "source": "kindle",
                },
            },
            {
                "id": 2,
                "text": "Test highlight 2",
                "highlighted_at": "2023-01-02T12:00:00Z",
                "updated": "2023-01-02T12:00:00Z",
                "book_id": 1,
                "tags": [],
            },
        ],
    }


@pytest.fixture
def api_response_books():
    """Sample API response for books endpoint."""
    return {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": 1,
                "title": "Test Book",
                "author": "Test Author",
                "category": "books",
                "source": "kindle",
                "num_highlights": 5,
                "last_highlight_at": "2023-01-01T12:00:00Z",
                "updated": "2023-01-01T12:00:00Z",
                "cover_image_url": "https://example.com/cover.jpg",
                "highlights_url": "https://example.com/highlights",
                "source_url": "https://example.com/book",
                "asin": "B123456789",
                "tags": [],
            },
        ],
    }
