"""SQLAlchemy models for storing Readwise data locally."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

Base = declarative_base()

# Association tables for many-to-many relationships
highlight_tags = Table(
    "highlight_tags",
    Base.metadata,
    Column("highlight_id", Integer, ForeignKey("highlights.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

book_tags = Table(
    "book_tags",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Book(Base):
    """Book/source model for storing book metadata."""
    __tablename__ = "books"

    # Readwise book ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Core book data
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    author: Mapped[Optional[str]] = mapped_column(String(300), index=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), index=True)

    # Metadata
    num_highlights: Mapped[int] = mapped_column(Integer, default=0)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(1000))
    highlights_url: Mapped[Optional[str]] = mapped_column(String(1000))
    source_url: Mapped[Optional[str]] = mapped_column(String(1000))
    asin: Mapped[Optional[str]] = mapped_column(String(20))

    # Timestamps
    last_highlight_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Local metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    highlights: Mapped[list["Highlight"]] = relationship("Highlight", back_populates="book")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary=book_tags, back_populates="books")

    # Indexes
    __table_args__ = (
        Index("idx_book_source_category", "source", "category"),
        Index("idx_book_author_title", "author", "title"),
    )

    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}', author='{self.author}')>"


class Highlight(Base):
    """Highlight model for storing individual highlights."""
    __tablename__ = "highlights"

    # Readwise highlight ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Core highlight data
    text: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[int]] = mapped_column(Integer)
    location_type: Mapped[Optional[str]] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(50))
    url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Foreign key to book
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"), nullable=False, index=True)

    # Timestamps
    highlighted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    updated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Local metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Full-text search support
    text_search: Mapped[Optional[str]] = mapped_column(String(1000))  # Simplified text for search

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="highlights")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary=highlight_tags, back_populates="highlights")

    # Indexes
    __table_args__ = (
        Index("idx_highlight_book_date", "book_id", "highlighted_at"),
        Index("idx_highlight_date", "highlighted_at"),
        Index("idx_highlight_text_search", "text_search"),
    )

    def __repr__(self):
        return f"<Highlight(id={self.id}, book_id={self.book_id}, text='{self.text[:50]}...')>"


class Tag(Base):
    """Tag model for categorizing highlights and books."""
    __tablename__ = "tags"

    # Readwise tag ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Tag data
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

    # Local metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Usage counts (calculated)
    highlight_count: Mapped[int] = mapped_column(Integer, default=0)
    book_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    highlights: Mapped[list["Highlight"]] = relationship(
        "Highlight", secondary=highlight_tags, back_populates="tags",
    )
    books: Mapped[list["Book"]] = relationship(
        "Book", secondary=book_tags, back_populates="tags",
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"


class SyncStatus(Base):
    """Track synchronization status with Readwise API."""
    __tablename__ = "sync_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Sync metadata
    sync_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'full', 'incremental'
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'running', 'completed', 'failed'

    # Sync results
    highlights_synced: Mapped[int] = mapped_column(Integer, default=0)
    books_synced: Mapped[int] = mapped_column(Integer, default=0)
    tags_synced: Mapped[int] = mapped_column(Integer, default=0)

    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Last successful sync timestamp for incremental syncs
    last_sync_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self):
        return f"<SyncStatus(id={self.id}, type='{self.sync_type}', status='{self.status}')>"


# Convenience aliases for association tables
HighlightTag = highlight_tags
BookTag = book_tags
