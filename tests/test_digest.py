"""Tests for the DigestService."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.readwise_digest import DigestService, ReadwiseClient
from src.readwise_digest.models import Book, Highlight


class TestDigestService:
    """Test cases for DigestService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=ReadwiseClient)
        self.digest_service = DigestService(self.mock_client)

        # Sample data
        self.sample_book = Book(
            id=1,
            title="Test Book",
            author="Test Author",
            source="kindle",
        )

        self.sample_highlights = [
            Highlight(
                id=1,
                text="First highlight",
                note="First note",
                highlighted_at=datetime(2023, 1, 1, 12, 0, 0),
                book_id=1,
                book=self.sample_book,
            ),
            Highlight(
                id=2,
                text="Second highlight",
                highlighted_at=datetime(2023, 1, 2, 12, 0, 0),
                book_id=1,
                book=self.sample_book,
            ),
        ]

    def test_get_all_highlights(self):
        """Test getting all highlights."""
        self.mock_client.get_highlights.return_value = iter(self.sample_highlights)

        highlights = self.digest_service.get_all_highlights()

        assert len(highlights) == 2
        assert highlights[0].text == "First highlight"
        assert highlights[1].text == "Second highlight"
        self.mock_client.get_highlights.assert_called_once_with(updated_after=None)

    def test_get_recent_highlights(self):
        """Test getting recent highlights."""
        self.mock_client.get_highlights.return_value = iter([self.sample_highlights[0]])

        with patch("src.readwise_digest.digest.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 13, 0, 0)

            highlights = self.digest_service.get_recent_highlights(hours=1)

        assert len(highlights) == 1
        assert highlights[0].text == "First highlight"

        # Check that highlighted_after was called with correct time
        call_args = self.mock_client.get_highlights.call_args
        assert "highlighted_after" in call_args.kwargs

    def test_get_highlights_with_notes(self):
        """Test filtering highlights with notes."""
        self.mock_client.get_highlights.return_value = iter(self.sample_highlights)

        highlights = self.digest_service.get_highlights_with_notes()

        # Only first highlight has a note
        assert len(highlights) == 1
        assert highlights[0].text == "First highlight"
        assert highlights[0].note == "First note"

    def test_get_highlights_by_source(self):
        """Test filtering highlights by source."""
        self.mock_client.get_highlights.return_value = iter(self.sample_highlights)

        highlights = self.digest_service.get_highlights_by_source("kindle")

        assert len(highlights) == 2  # Both highlights are from kindle
        for highlight in highlights:
            assert highlight.book.source == "kindle"

    def test_create_digest_stats(self):
        """Test digest statistics creation."""
        stats = self.digest_service.create_digest_stats(
            highlights=self.sample_highlights,
            time_range="test range",
            execution_time=1.5,
        )

        assert stats.total_highlights == 2
        assert stats.total_books == 1  # Both highlights from same book
        assert stats.execution_time == 1.5
        assert stats.time_range == "test range"
        assert "kindle" in stats.books_by_source
        assert stats.books_by_source["kindle"] == 2

    def test_export_markdown(self):
        """Test markdown export."""
        markdown = self.digest_service.export_digest(
            highlights=self.sample_highlights,
            format="markdown",
            group_by="book",
        )

        assert "# Readwise Highlights Digest" in markdown
        assert "## Test Book" in markdown
        assert "First highlight" in markdown
        assert "Second highlight" in markdown
        assert "*Note: First note*" in markdown

    def test_export_json(self):
        """Test JSON export."""
        import json

        json_str = self.digest_service.export_digest(
            highlights=self.sample_highlights,
            format="json",
        )

        data = json.loads(json_str)

        assert data["total_highlights"] == 2
        assert len(data["highlights"]) == 2
        assert data["highlights"][0]["text"] == "First highlight"
        assert data["highlights"][0]["note"] == "First note"

    def test_export_csv(self):
        """Test CSV export."""
        csv_str = self.digest_service.export_digest(
            highlights=self.sample_highlights,
            format="csv",
        )

        lines = csv_str.strip().split("\n")
        assert len(lines) == 3  # Header + 2 data rows

        # Check header
        header = lines[0]
        assert "id" in header
        assert "text" in header
        assert "book_title" in header

        # Check data
        assert "First highlight" in lines[1]
        assert "Second highlight" in lines[2]

    def test_export_txt(self):
        """Test plain text export."""
        txt = self.digest_service.export_digest(
            highlights=self.sample_highlights,
            format="txt",
            group_by="book",
        )

        assert "Readwise Highlights Digest" in txt
        assert "Book: Test Book" in txt
        assert "1. First highlight" in txt
        assert "2. Second highlight" in txt
        assert "Note: First note" in txt

    def test_export_unsupported_format(self):
        """Test error on unsupported export format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            self.digest_service.export_digest(
                highlights=self.sample_highlights,
                format="xml",
            )

    def test_enrich_with_book_data(self):
        """Test enriching highlights with book data."""
        # Create highlight without book data
        highlight_without_book = Highlight(
            id=3,
            text="Third highlight",
            book_id=1,
            book=None,
        )

        self.mock_client.get_book.return_value = self.sample_book

        highlights = [highlight_without_book]
        self.digest_service._enrich_with_book_data(highlights)

        assert highlights[0].book is not None
        assert highlights[0].book.title == "Test Book"
        self.mock_client.get_book.assert_called_once_with(1)
