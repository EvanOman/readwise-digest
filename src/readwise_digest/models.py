"""Data models for Readwise API entities."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class HighlightLocation(Enum):
    """Location types for highlights."""
    KINDLE = "kindle"
    INSTAPAPER = "instapaper"
    POCKET = "pocket"
    IBOOKS = "ibooks"
    MANUAL = "manual"
    TWITTER = "twitter"
    READWISE = "readwise"
    AIRR = "airr"
    MATTER = "matter"
    OMNIVORE = "omnivore"


@dataclass
class Tag:
    """Represents a tag associated with highlights or books."""
    id: int
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tag":
        return cls(
            id=data["id"],
            name=data["name"],
        )


@dataclass
class Book:
    """Represents a book in Readwise."""
    id: int
    title: str
    author: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    num_highlights: int = 0
    last_highlight_at: Optional[datetime] = None
    updated: Optional[datetime] = None
    cover_image_url: Optional[str] = None
    highlights_url: Optional[str] = None
    source_url: Optional[str] = None
    asin: Optional[str] = None
    tags: list[Tag] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Book":
        return cls(
            id=data["id"],
            title=data["title"],
            author=data.get("author"),
            category=data.get("category"),
            source=data.get("source"),
            num_highlights=data.get("num_highlights", 0),
            last_highlight_at=cls._parse_datetime(data.get("last_highlight_at")),
            updated=cls._parse_datetime(data.get("updated")),
            cover_image_url=data.get("cover_image_url"),
            highlights_url=data.get("highlights_url"),
            source_url=data.get("source_url"),
            asin=data.get("asin"),
            tags=[Tag.from_dict(tag) for tag in data.get("tags", [])],
        )

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None


@dataclass
class Highlight:
    """Represents a highlight from Readwise."""
    id: int
    text: str
    note: Optional[str] = None
    location: Optional[int] = None
    location_type: Optional[HighlightLocation] = None
    highlighted_at: Optional[datetime] = None
    updated: Optional[datetime] = None
    book_id: Optional[int] = None
    url: Optional[str] = None
    color: Optional[str] = None
    tags: list[Tag] = field(default_factory=list)
    book: Optional[Book] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Highlight":
        location_type = None
        if data.get("location_type"):
            try:
                location_type = HighlightLocation(data["location_type"])
            except ValueError:
                location_type = None

        book = None
        if data.get("book"):
            book = Book.from_dict(data["book"])

        return cls(
            id=data["id"],
            text=data["text"],
            note=data.get("note"),
            location=data.get("location"),
            location_type=location_type,
            highlighted_at=cls._parse_datetime(data.get("highlighted_at")),
            updated=cls._parse_datetime(data.get("updated")),
            book_id=data.get("book_id"),
            url=data.get("url"),
            color=data.get("color"),
            tags=[Tag.from_dict(tag) for tag in data.get("tags", [])],
            book=book,
        )

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
