"""Tests for data models."""

import pytest
from datetime import datetime

from readwise_digest.models import Highlight, Book, Tag, HighlightLocation


class TestTag:
    """Test cases for Tag model."""
    
    def test_from_dict(self):
        """Test Tag creation from dictionary."""
        data = {
            "id": 1,
            "name": "important"
        }
        
        tag = Tag.from_dict(data)
        
        assert tag.id == 1
        assert tag.name == "important"


class TestBook:
    """Test cases for Book model."""
    
    def test_from_dict_complete(self):
        """Test Book creation from complete dictionary."""
        data = {
            "id": 1,
            "title": "Test Book",
            "author": "Test Author",
            "category": "books",
            "source": "kindle",
            "num_highlights": 5,
            "last_highlight_at": "2023-01-01T12:00:00Z",
            "updated": "2023-01-02T12:00:00Z",
            "cover_image_url": "https://example.com/cover.jpg",
            "highlights_url": "https://example.com/highlights",
            "source_url": "https://example.com/book",
            "asin": "B123456789",
            "tags": [
                {"id": 1, "name": "fiction"},
                {"id": 2, "name": "favorite"}
            ]
        }
        
        book = Book.from_dict(data)
        
        assert book.id == 1
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.category == "books"
        assert book.source == "kindle"
        assert book.num_highlights == 5
        assert isinstance(book.last_highlight_at, datetime)
        assert isinstance(book.updated, datetime)
        assert book.cover_image_url == "https://example.com/cover.jpg"
        assert book.asin == "B123456789"
        assert len(book.tags) == 2
        assert book.tags[0].name == "fiction"
    
    def test_from_dict_minimal(self):
        """Test Book creation from minimal dictionary."""
        data = {
            "id": 1,
            "title": "Minimal Book"
        }
        
        book = Book.from_dict(data)
        
        assert book.id == 1
        assert book.title == "Minimal Book"
        assert book.author is None
        assert book.num_highlights == 0
        assert book.tags == []
    
    def test_parse_datetime_invalid(self):
        """Test datetime parsing with invalid format."""
        result = Book._parse_datetime("invalid-date")
        assert result is None
    
    def test_parse_datetime_none(self):
        """Test datetime parsing with None input."""
        result = Book._parse_datetime(None)
        assert result is None


class TestHighlight:
    """Test cases for Highlight model."""
    
    def test_from_dict_complete(self):
        """Test Highlight creation from complete dictionary."""
        data = {
            "id": 1,
            "text": "This is a highlight",
            "note": "This is a note",
            "location": 42,
            "location_type": "kindle",
            "highlighted_at": "2023-01-01T12:00:00Z",
            "updated": "2023-01-02T12:00:00Z",
            "book_id": 10,
            "url": "https://example.com/highlight",
            "color": "yellow",
            "tags": [
                {"id": 1, "name": "important"}
            ],
            "book": {
                "id": 10,
                "title": "Source Book",
                "author": "Book Author"
            }
        }
        
        highlight = Highlight.from_dict(data)
        
        assert highlight.id == 1
        assert highlight.text == "This is a highlight"
        assert highlight.note == "This is a note"
        assert highlight.location == 42
        assert highlight.location_type == HighlightLocation.KINDLE
        assert isinstance(highlight.highlighted_at, datetime)
        assert isinstance(highlight.updated, datetime)
        assert highlight.book_id == 10
        assert highlight.url == "https://example.com/highlight"
        assert highlight.color == "yellow"
        assert len(highlight.tags) == 1
        assert highlight.tags[0].name == "important"
        assert highlight.book is not None
        assert highlight.book.title == "Source Book"
    
    def test_from_dict_minimal(self):
        """Test Highlight creation from minimal dictionary."""
        data = {
            "id": 1,
            "text": "Minimal highlight"
        }
        
        highlight = Highlight.from_dict(data)
        
        assert highlight.id == 1
        assert highlight.text == "Minimal highlight"
        assert highlight.note is None
        assert highlight.location_type is None
        assert highlight.tags == []
        assert highlight.book is None
    
    def test_location_type_invalid(self):
        """Test handling of invalid location type."""
        data = {
            "id": 1,
            "text": "Test highlight",
            "location_type": "invalid_source"
        }
        
        highlight = Highlight.from_dict(data)
        
        assert highlight.location_type is None
    
    def test_parse_datetime_with_microseconds(self):
        """Test datetime parsing with microseconds."""
        result = Highlight._parse_datetime("2023-01-01T12:00:00.123456Z")
        assert isinstance(result, datetime)
        assert result.microsecond == 123456
    
    def test_parse_datetime_iso_format(self):
        """Test datetime parsing with various ISO formats."""
        test_cases = [
            "2023-01-01T12:00:00Z",
            "2023-01-01T12:00:00.123Z",
            "2023-01-01T12:00:00+00:00",
            "2023-01-01T12:00:00.123456+00:00"
        ]
        
        for date_str in test_cases:
            result = Highlight._parse_datetime(date_str)
            assert isinstance(result, datetime)


class TestHighlightLocation:
    """Test cases for HighlightLocation enum."""
    
    def test_enum_values(self):
        """Test that all expected location types are available."""
        expected_values = [
            "kindle", "instapaper", "pocket", "ibooks", "manual",
            "twitter", "readwise", "airr", "matter", "omnivore"
        ]
        
        for value in expected_values:
            location = HighlightLocation(value)
            assert location.value == value
    
    def test_enum_invalid_value(self):
        """Test handling of invalid location type value."""
        with pytest.raises(ValueError):
            HighlightLocation("invalid_location")