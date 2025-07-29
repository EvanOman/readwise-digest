"""Database synchronization service for Readwise data."""

import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..client import ReadwiseClient
from ..digest import DigestService
from ..logging_config import get_logger
from .database import get_session_factory
from .models import Book, Highlight, SyncStatus, Tag

logger = get_logger(__name__)


class DatabaseSync:
    """Service for synchronizing Readwise data to local database."""

    def __init__(self, client: ReadwiseClient):
        self.client = client
        self.digest_service = DigestService(client)
        self.SessionLocal = get_session_factory()

    def sync_all(self, force: bool = False) -> dict[str, Any]:
        """Perform a full synchronization of all data.

        Args:
            force: If True, sync all data regardless of last sync time

        Returns:
            Dictionary with sync results and statistics
        """
        logger.info("Starting full synchronization")

        with self.SessionLocal() as session:
            # Create sync status record
            sync_record = SyncStatus(
                sync_type="full",
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            session.add(sync_record)
            session.commit()

            try:
                results = {
                    "sync_id": sync_record.id,
                    "started_at": sync_record.started_at,
                    "books_synced": 0,
                    "highlights_synced": 0,
                    "tags_synced": 0,
                    "errors": [],
                }

                # Sync books first
                logger.info("Syncing books...")
                books_result = self._sync_books(session, force=force)
                results["books_synced"] = books_result["synced"]
                results["errors"].extend(books_result["errors"])

                # Sync highlights
                logger.info("Syncing highlights...")
                highlights_result = self._sync_highlights(session, force=force)
                results["highlights_synced"] = highlights_result["synced"]
                results["errors"].extend(highlights_result["errors"])

                # Sync tags
                logger.info("Syncing tags...")
                tags_result = self._sync_tags(session)
                results["tags_synced"] = tags_result["synced"]
                results["errors"].extend(tags_result["errors"])

                # Update sync record
                sync_record.status = "completed"
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.books_synced = results["books_synced"]
                sync_record.highlights_synced = results["highlights_synced"]
                sync_record.tags_synced = results["tags_synced"]
                sync_record.last_sync_timestamp = datetime.now(timezone.utc)

                if results["errors"]:
                    sync_record.error_message = f"{len(results['errors'])} errors occurred"

                session.commit()

                results["completed_at"] = sync_record.completed_at
                results["duration"] = (sync_record.completed_at - sync_record.started_at).total_seconds()

                logger.info(f"Full sync completed: {results['highlights_synced']} highlights, "
                           f"{results['books_synced']} books, {results['tags_synced']} tags")

                return results

            except Exception as e:
                logger.error(f"Sync failed: {e}")
                sync_record.status = "failed"
                sync_record.error_message = str(e)
                sync_record.completed_at = datetime.now(timezone.utc)
                session.commit()
                raise

    def sync_incremental(self, hours: int = 24) -> dict[str, Any]:
        """Perform incremental sync of recent data.

        Args:
            hours: Number of hours to look back for updates

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting incremental sync (last {hours} hours)")

        with self.SessionLocal() as session:
            # Create sync status record
            sync_record = SyncStatus(
                sync_type="incremental",
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            session.add(sync_record)
            session.commit()

            try:
                # Get recent highlights
                recent_highlights = self.digest_service.get_recent_highlights(
                    hours=hours, include_books=True,
                )

                results = {
                    "sync_id": sync_record.id,
                    "started_at": sync_record.started_at,
                    "highlights_processed": len(recent_highlights),
                    "highlights_synced": 0,
                    "books_synced": 0,
                    "errors": [],
                }

                # Process recent highlights
                books_synced = set()  # Track which books we've synced
                for highlight_data in recent_highlights:
                    try:
                        # Sync the book first (if not already synced)
                        if highlight_data.book and highlight_data.book.id not in books_synced:
                            book = self._upsert_book(session, highlight_data.book)
                            books_synced.add(highlight_data.book.id)
                            session.flush()  # Flush to handle any conflicts immediately

                        # Sync the highlight
                        self._upsert_highlight(session, highlight_data)
                        results["highlights_synced"] += 1
                        session.flush()  # Flush each highlight individually

                    except Exception as e:
                        session.rollback()  # Rollback this highlight and continue
                        error_msg = f"Error syncing highlight {highlight_data.id}: {e}"
                        logger.warning(error_msg)
                        results["errors"].append(error_msg)

                results["books_synced"] = len(books_synced)

                # Update sync record
                sync_record.status = "completed"
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.highlights_synced = results["highlights_synced"]
                sync_record.books_synced = results["books_synced"]
                sync_record.last_sync_timestamp = datetime.now(timezone.utc)

                session.commit()

                results["completed_at"] = sync_record.completed_at
                results["duration"] = (sync_record.completed_at - sync_record.started_at).total_seconds()

                logger.info(f"Incremental sync completed: {results['highlights_synced']} highlights")

                return results

            except Exception as e:
                logger.error(f"Incremental sync failed: {e}")
                sync_record.status = "failed"
                sync_record.error_message = str(e)
                sync_record.completed_at = datetime.now(timezone.utc)
                session.commit()
                raise

    def _sync_books(self, session: Session, force: bool = False) -> dict[str, Any]:
        """Sync all books from Readwise."""
        results = {"synced": 0, "errors": []}

        try:
            # Get updated_after timestamp if not forcing full sync
            updated_after = None
            if not force:
                last_sync = session.query(SyncStatus).filter(
                    and_(SyncStatus.status == "completed", SyncStatus.sync_type == "full"),
                ).order_by(SyncStatus.completed_at.desc()).first()

                if last_sync and last_sync.last_sync_timestamp:
                    updated_after = last_sync.last_sync_timestamp

            # Fetch books from API
            books = list(self.client.get_books(updated_after=updated_after))

            for book_data in books:
                try:
                    self._upsert_book(session, book_data)
                    results["synced"] += 1
                except Exception as e:
                    error_msg = f"Error syncing book {book_data.id}: {e}"
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)

            session.commit()

        except Exception as e:
            logger.error(f"Failed to sync books: {e}")
            results["errors"].append(f"Book sync failed: {e}")

        return results

    def _sync_highlights(self, session: Session, force: bool = False) -> dict[str, Any]:
        """Sync all highlights from Readwise."""
        results = {"synced": 0, "errors": []}

        try:
            # Get updated_after timestamp if not forcing full sync
            updated_after = None
            if not force:
                last_sync = session.query(SyncStatus).filter(
                    and_(SyncStatus.status == "completed", SyncStatus.sync_type == "full"),
                ).order_by(SyncStatus.completed_at.desc()).first()

                if last_sync and last_sync.last_sync_timestamp:
                    updated_after = last_sync.last_sync_timestamp

            # Fetch highlights from API
            highlights = list(self.client.get_highlights(updated_after=updated_after))

            for highlight_data in highlights:
                try:
                    # Ensure book exists
                    if highlight_data.book_id:
                        book = session.query(Book).filter(Book.id == highlight_data.book_id).first()
                        if not book:
                            # Fetch book data if not exists
                            try:
                                book_data = self.client.get_book(highlight_data.book_id)
                                self._upsert_book(session, book_data)
                            except Exception as e:
                                logger.warning(f"Could not fetch book {highlight_data.book_id}: {e}")

                    self._upsert_highlight(session, highlight_data)
                    results["synced"] += 1

                except Exception as e:
                    error_msg = f"Error syncing highlight {highlight_data.id}: {e}"
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)

            session.commit()

        except Exception as e:
            logger.error(f"Failed to sync highlights: {e}")
            results["errors"].append(f"Highlight sync failed: {e}")

        return results

    def _sync_tags(self, session: Session) -> dict[str, Any]:
        """Sync tags from existing highlights and books."""
        results = {"synced": 0, "errors": []}

        try:
            # Get all unique tags from highlights and books in database
            highlight_tags = session.query(Highlight).all()
            book_tags = session.query(Book).all()

            all_tags = set()

            # Collect tag data from highlights and books
            for highlight in highlight_tags:
                for tag in highlight.tags:
                    all_tags.add((tag.id, tag.name))

            for book in book_tags:
                for tag in book.tags:
                    all_tags.add((tag.id, tag.name))

            # Upsert tags
            for tag_id, tag_name in all_tags:
                try:
                    self._upsert_tag(session, tag_id, tag_name)
                    results["synced"] += 1
                except Exception as e:
                    error_msg = f"Error syncing tag {tag_name}: {e}"
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)

            session.commit()

        except Exception as e:
            logger.error(f"Failed to sync tags: {e}")
            results["errors"].append(f"Tag sync failed: {e}")

        return results

    def _upsert_book(self, session: Session, book_data) -> Book:
        """Insert or update a book record."""
        # Check if book exists
        book = session.query(Book).filter(Book.id == book_data.id).first()

        if book:
            # Update existing book
            book.title = book_data.title
            book.author = book_data.author
            book.category = book_data.category
            book.source = book_data.source
            book.num_highlights = book_data.num_highlights
            book.cover_image_url = book_data.cover_image_url
            book.highlights_url = book_data.highlights_url
            book.source_url = book_data.source_url
            book.asin = book_data.asin
            book.last_highlight_at = book_data.last_highlight_at
            book.updated = book_data.updated
            book.synced_at = datetime.now(timezone.utc)
        else:
            # Create new book
            book = Book(
                id=book_data.id,
                title=book_data.title,
                author=book_data.author,
                category=book_data.category,
                source=book_data.source,
                num_highlights=book_data.num_highlights,
                cover_image_url=book_data.cover_image_url,
                highlights_url=book_data.highlights_url,
                source_url=book_data.source_url,
                asin=book_data.asin,
                last_highlight_at=book_data.last_highlight_at,
                updated=book_data.updated,
                synced_at=datetime.now(timezone.utc),
            )
            session.add(book)

        # Handle tags
        if book_data.tags:
            book.tags.clear()  # Clear existing tags
            for tag_data in book_data.tags:
                tag = self._upsert_tag(session, tag_data.id, tag_data.name)
                book.tags.append(tag)

        return book

    def _upsert_highlight(self, session: Session, highlight_data) -> Highlight:
        """Insert or update a highlight record."""
        # Check if highlight exists
        highlight = session.query(Highlight).filter(Highlight.id == highlight_data.id).first()

        # Create search text for full-text search
        search_text = self._create_search_text(highlight_data.text, highlight_data.note)

        if highlight:
            # Update existing highlight
            highlight.text = highlight_data.text
            highlight.note = highlight_data.note
            highlight.location = highlight_data.location
            highlight.location_type = highlight_data.location_type.value if highlight_data.location_type else None
            highlight.color = highlight_data.color
            highlight.url = highlight_data.url
            highlight.book_id = highlight_data.book_id
            highlight.highlighted_at = highlight_data.highlighted_at
            highlight.updated = highlight_data.updated
            highlight.text_search = search_text
            highlight.synced_at = datetime.now(timezone.utc)
        else:
            # Create new highlight
            highlight = Highlight(
                id=highlight_data.id,
                text=highlight_data.text,
                note=highlight_data.note,
                location=highlight_data.location,
                location_type=highlight_data.location_type.value if highlight_data.location_type else None,
                color=highlight_data.color,
                url=highlight_data.url,
                book_id=highlight_data.book_id,
                highlighted_at=highlight_data.highlighted_at,
                updated=highlight_data.updated,
                text_search=search_text,
                synced_at=datetime.now(timezone.utc),
            )
            session.add(highlight)

        # Handle tags
        if highlight_data.tags:
            highlight.tags.clear()  # Clear existing tags
            for tag_data in highlight_data.tags:
                tag = self._upsert_tag(session, tag_data.id, tag_data.name)
                highlight.tags.append(tag)

        return highlight

    def _upsert_tag(self, session: Session, tag_id: int, tag_name: str) -> Tag:
        """Insert or update a tag record."""
        # Check if tag exists
        tag = session.query(Tag).filter(Tag.id == tag_id).first()

        if tag:
            # Update existing tag
            tag.name = tag_name
            tag.synced_at = datetime.now(timezone.utc)
        else:
            # Create new tag
            tag = Tag(
                id=tag_id,
                name=tag_name,
                synced_at=datetime.now(timezone.utc),
            )
            session.add(tag)

        return tag

    def _create_search_text(self, text: str, note: Optional[str] = None) -> str:
        """Create simplified search text by removing markdown and limiting length."""
        # Combine text and note
        combined = text
        if note:
            combined += " " + note

        # Remove markdown formatting
        # Remove bold/italic markers
        combined = re.sub(r"\*\*([^*]+)\*\*", r"\1", combined)  # **bold**
        combined = re.sub(r"\*([^*]+)\*", r"\1", combined)      # *italic*
        combined = re.sub(r"_([^_]+)_", r"\1", combined)        # _italic_

        # Remove links
        combined = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", combined)  # [text](url)

        # Remove code blocks
        combined = re.sub(r"`([^`]+)`", r"\1", combined)  # `code`

        # Normalize whitespace
        combined = re.sub(r"\s+", " ", combined).strip()

        # Limit length for database storage
        return combined[:1000] if len(combined) > 1000 else combined

    def get_sync_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent sync history."""
        with self.SessionLocal() as session:
            syncs = session.query(SyncStatus).order_by(
                SyncStatus.started_at.desc(),
            ).limit(limit).all()

            return [
                {
                    "id": sync.id,
                    "type": sync.sync_type,
                    "status": sync.status,
                    "started_at": sync.started_at,
                    "completed_at": sync.completed_at,
                    "duration": (sync.completed_at - sync.started_at).total_seconds() if sync.completed_at else None,
                    "highlights_synced": sync.highlights_synced,
                    "books_synced": sync.books_synced,
                    "tags_synced": sync.tags_synced,
                    "error_message": sync.error_message,
                }
                for sync in syncs
            ]
