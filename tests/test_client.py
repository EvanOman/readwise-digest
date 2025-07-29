"""Tests for the ReadwiseClient."""

from unittest.mock import patch

import pytest
import responses

from src.readwise_digest import AuthenticationError, RateLimitError, ReadwiseClient
from src.readwise_digest.models import Book, Highlight


class TestReadwiseClient:
    """Test cases for ReadwiseClient."""

    def setup_method(self):
        """Set up test client."""
        # Create client with no retries to avoid issues in tests
        self.client = ReadwiseClient(api_key="test_api_key", max_retries=0)

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = ReadwiseClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert "Token test_key" in client.session.headers["Authorization"]

    def test_init_without_api_key_raises_error(self):
        """Test client initialization without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                ReadwiseClient()

    @patch.dict("os.environ", {"READWISE_API_KEY": "env_api_key"})
    def test_init_with_env_api_key(self):
        """Test client initialization with environment variable API key."""
        client = ReadwiseClient()
        assert client.api_key == "env_api_key"

    @responses.activate
    def test_get_highlights_success(self):
        """Test successful highlights retrieval."""
        mock_response = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": 1,
                    "text": "Test highlight 1",
                    "note": "Test note",
                    "highlighted_at": "2023-01-01T12:00:00Z",
                    "updated": "2023-01-01T12:00:00Z",
                    "book_id": 1,
                    "url": "https://example.com",
                },
                {
                    "id": 2,
                    "text": "Test highlight 2",
                    "highlighted_at": "2023-01-02T12:00:00Z",
                    "updated": "2023-01-02T12:00:00Z",
                    "book_id": 1,
                },
            ],
        }

        responses.add(
            responses.GET,
            "https://readwise.io/api/v2/highlights/",
            json=mock_response,
            status=200,
        )

        highlights = list(self.client.get_highlights())

        assert len(highlights) == 2
        assert isinstance(highlights[0], Highlight)
        assert highlights[0].text == "Test highlight 1"
        assert highlights[0].note == "Test note"
        assert highlights[1].text == "Test highlight 2"

    @responses.activate
    def test_get_books_success(self):
        """Test successful books retrieval."""
        mock_response = {
            "count": 1,
            "next": None,
            "results": [
                {
                    "id": 1,
                    "title": "Test Book",
                    "author": "Test Author",
                    "category": "books",
                    "source": "kindle",
                    "num_highlights": 5,
                    "updated": "2023-01-01T12:00:00Z",
                },
            ],
        }

        responses.add(
            responses.GET,
            "https://readwise.io/api/v2/books/",
            json=mock_response,
            status=200,
        )

        books = list(self.client.get_books())

        assert len(books) == 1
        assert isinstance(books[0], Book)
        assert books[0].title == "Test Book"
        assert books[0].author == "Test Author"

    @responses.activate
    def test_authentication_error(self):
        """Test authentication error handling."""
        responses.add(
            responses.GET,
            "https://readwise.io/api/v2/highlights/",
            json={"detail": "Invalid token"},
            status=401,
        )

        with pytest.raises(AuthenticationError):
            list(self.client.get_highlights())

    def test_rate_limit_error(self):
        """Test rate limit error handling."""
        # Create a mock response object
        from unittest.mock import Mock
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {"detail": "Rate limit exceeded"}
        mock_response.content = True

        # Mock the session.request method to return our mock response
        with patch.object(self.client.session, "request", return_value=mock_response):
            with pytest.raises(RateLimitError) as exc_info:
                list(self.client.get_highlights())

        assert exc_info.value.retry_after == 60

    @responses.activate
    def test_pagination(self):
        """Test pagination handling."""
        # First page
        responses.add(
            responses.GET,
            "https://readwise.io/api/v2/highlights/",
            json={
                "count": 2,
                "next": "https://readwise.io/api/v2/highlights/?page=2",
                "results": [
                    {
                        "id": 1,
                        "text": "Highlight 1",
                        "highlighted_at": "2023-01-01T12:00:00Z",
                        "updated": "2023-01-01T12:00:00Z",
                        "book_id": 1,
                    },
                ],
            },
            status=200,
        )

        # Second page
        responses.add(
            responses.GET,
            "https://readwise.io/api/v2/highlights/?page=2",
            json={
                "count": 2,
                "next": None,
                "results": [
                    {
                        "id": 2,
                        "text": "Highlight 2",
                        "highlighted_at": "2023-01-02T12:00:00Z",
                        "updated": "2023-01-02T12:00:00Z",
                        "book_id": 1,
                    },
                ],
            },
            status=200,
        )

        highlights = list(self.client.get_highlights())

        assert len(highlights) == 2
        assert highlights[0].text == "Highlight 1"
        assert highlights[1].text == "Highlight 2"

    @responses.activate
    def test_create_highlight(self):
        """Test highlight creation."""
        mock_response = {
            "id": 123,
            "text": "New highlight",
            "note": "New note",
            "highlighted_at": "2023-01-01T12:00:00Z",
            "updated": "2023-01-01T12:00:00Z",
            "book_id": 1,
        }

        responses.add(
            responses.POST,
            "https://readwise.io/api/v2/highlights/",
            json=[mock_response],  # API returns array
            status=201,
        )

        highlight = self.client.create_highlight(
            text="New highlight",
            title="Test Book",
            note="New note",
        )

        assert isinstance(highlight, Highlight)
        assert highlight.text == "New highlight"
        assert highlight.note == "New note"

    def test_close(self):
        """Test client session closure."""
        with patch.object(self.client.session, "close") as mock_close:
            self.client.close()
            mock_close.assert_called_once()
