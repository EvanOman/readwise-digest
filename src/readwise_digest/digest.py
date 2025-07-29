"""Digest service for retrieving and processing Readwise highlights."""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Union

from .client import ReadwiseClient
from .exceptions import ReadwiseError
from .models import Highlight


@dataclass
class DigestStats:
    """Statistics for a digest operation."""

    total_highlights: int
    total_books: int
    new_highlights: int
    updated_highlights: int
    time_range: str
    execution_time: float
    books_by_source: dict[str, int]
    highlights_by_date: dict[str, int]


class DigestService:
    """Service for creating digests of Readwise highlights."""

    def __init__(self, client: ReadwiseClient):
        self.client = client
        self.logger = logging.getLogger(__name__)

    def get_all_highlights(
        self,
        include_books: bool = True,
        updated_after: Optional[Union[datetime, str]] = None,
    ) -> list[Highlight]:
        """Get all highlights, optionally filtered by update time."""
        start_time = datetime.now()
        self.logger.info("Starting full highlights digest")

        try:
            highlights = list(
                self.client.get_highlights(
                    updated_after=updated_after,
                )
            )

            if include_books:
                self._enrich_with_book_data(highlights)

            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Retrieved {len(highlights)} highlights in {execution_time:.2f}s")

            return highlights

        except ReadwiseError as e:
            self.logger.error(f"Failed to retrieve highlights: {e}")
            raise

    def get_recent_highlights(
        self,
        hours: int = 24,
        include_books: bool = True,
        use_highlighted_at: bool = True,
    ) -> list[Highlight]:
        """Get highlights from the last X hours.

        Args:
            hours: Number of hours to look back
            include_books: Whether to include full book data
            use_highlighted_at: If True, filter by highlighted_at; if False, filter by updated
        """
        start_time = datetime.now()
        cutoff_time = datetime.now() - timedelta(hours=hours)

        self.logger.info(f"Getting highlights from last {hours} hours (since {cutoff_time})")

        try:
            if use_highlighted_at:
                highlights = list(
                    self.client.get_highlights(
                        highlighted_after=cutoff_time,
                    )
                )
            else:
                highlights = list(
                    self.client.get_highlights(
                        updated_after=cutoff_time,
                    )
                )

            if include_books:
                self._enrich_with_book_data(highlights)

            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Retrieved {len(highlights)} recent highlights in {execution_time:.2f}s"
            )

            return highlights

        except ReadwiseError as e:
            self.logger.error(f"Failed to retrieve recent highlights: {e}")
            raise

    def get_highlights_by_book(
        self,
        book_id: int,
        updated_after: Optional[Union[datetime, str]] = None,
    ) -> list[Highlight]:
        """Get all highlights for a specific book."""
        self.logger.info(f"Getting highlights for book {book_id}")

        try:
            highlights = list(
                self.client.get_highlights(
                    book_id=book_id,
                    updated_after=updated_after,
                )
            )

            self.logger.info(f"Retrieved {len(highlights)} highlights for book {book_id}")
            return highlights

        except ReadwiseError as e:
            self.logger.error(f"Failed to retrieve highlights for book {book_id}: {e}")
            raise

    def get_highlights_with_notes(self, hours: Optional[int] = None) -> list[Highlight]:
        """Get highlights that have notes attached."""
        if hours:
            highlights = self.get_recent_highlights(hours, include_books=True)
        else:
            highlights = self.get_all_highlights(include_books=True)

        noted_highlights = [h for h in highlights if h.note and h.note.strip()]
        self.logger.info(f"Found {len(noted_highlights)} highlights with notes")

        return noted_highlights

    def get_highlights_by_source(
        self,
        source: str,
        hours: Optional[int] = None,
    ) -> list[Highlight]:
        """Get highlights from a specific source (e.g., 'kindle', 'twitter')."""
        if hours:
            highlights = self.get_recent_highlights(hours, include_books=True)
        else:
            highlights = self.get_all_highlights(include_books=True)

        source_highlights = [
            h
            for h in highlights
            if h.book and h.book.source and h.book.source.lower() == source.lower()
        ]

        self.logger.info(f"Found {len(source_highlights)} highlights from {source}")
        return source_highlights

    def create_digest_stats(
        self,
        highlights: list[Highlight],
        time_range: str,
        execution_time: float,
        previous_highlights: Optional[list[Highlight]] = None,
    ) -> DigestStats:
        """Create statistics for a digest operation."""
        books = {h.book_id for h in highlights if h.book_id}

        # Count highlights by source
        books_by_source = defaultdict(int)
        for highlight in highlights:
            if highlight.book and highlight.book.source:
                books_by_source[highlight.book.source] += 1
            else:
                books_by_source["unknown"] += 1

        # Count highlights by date
        highlights_by_date = defaultdict(int)
        for highlight in highlights:
            if highlight.highlighted_at:
                date_key = highlight.highlighted_at.strftime("%Y-%m-%d")
                highlights_by_date[date_key] += 1
            elif highlight.updated:
                date_key = highlight.updated.strftime("%Y-%m-%d")
                highlights_by_date[date_key] += 1

        # Calculate new vs updated highlights
        new_highlights = len(highlights)
        updated_highlights = 0

        if previous_highlights:
            previous_ids = {h.id for h in previous_highlights}
            current_ids = {h.id for h in highlights}
            new_highlights = len(current_ids - previous_ids)
            updated_highlights = len(current_ids & previous_ids)

        return DigestStats(
            total_highlights=len(highlights),
            total_books=len(books),
            new_highlights=new_highlights,
            updated_highlights=updated_highlights,
            time_range=time_range,
            execution_time=execution_time,
            books_by_source=dict(books_by_source),
            highlights_by_date=dict(highlights_by_date),
        )

    def _enrich_with_book_data(self, highlights: list[Highlight]):
        """Enrich highlights with full book data where missing."""
        book_cache = {}
        enriched_count = 0

        for highlight in highlights:
            if highlight.book_id and not highlight.book:
                if highlight.book_id not in book_cache:
                    try:
                        book_cache[highlight.book_id] = self.client.get_book(highlight.book_id)
                    except ReadwiseError as e:
                        self.logger.warning(f"Failed to get book {highlight.book_id}: {e}")
                        continue

                if highlight.book_id in book_cache:
                    highlight.book = book_cache[highlight.book_id]
                    enriched_count += 1

        if enriched_count > 0:
            self.logger.info(f"Enriched {enriched_count} highlights with book data")

    def export_digest(
        self,
        highlights: list[Highlight],
        format: str = "markdown",
        group_by: str = "book",
    ) -> str:
        """Export highlights in various formats.

        Args:
            highlights: List of highlights to export
            format: Export format ('markdown', 'json', 'csv', 'txt')
            group_by: How to group highlights ('book', 'date', 'source', 'none')
        """
        if format.lower() == "markdown":
            return self._export_markdown(highlights, group_by)
        if format.lower() == "json":
            return self._export_json(highlights)
        if format.lower() == "csv":
            return self._export_csv(highlights)
        if format.lower() == "txt":
            return self._export_txt(highlights, group_by)
        raise ValueError(f"Unsupported format: {format}")

    def _export_markdown(self, highlights: list[Highlight], group_by: str) -> str:
        """Export highlights as Markdown."""
        output = ["# Readwise Highlights Digest\n"]
        output.append(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.append(f"Total highlights: {len(highlights)}\n")

        if group_by == "book":
            books = defaultdict(list)
            for highlight in highlights:
                book_title = highlight.book.title if highlight.book else "Unknown Book"
                books[book_title].append(highlight)

            for book_title, book_highlights in books.items():
                output.append(f"\n## {book_title}\n")
                for highlight in book_highlights:
                    output.append(f"- {highlight.text}")
                    if highlight.note:
                        output.append(f"  - *Note: {highlight.note}*")
                    output.append("")

        elif group_by == "date":
            dates = defaultdict(list)
            for highlight in highlights:
                date_key = "Unknown Date"
                if highlight.highlighted_at:
                    date_key = highlight.highlighted_at.strftime("%Y-%m-%d")
                elif highlight.updated:
                    date_key = highlight.updated.strftime("%Y-%m-%d")
                dates[date_key].append(highlight)

            for date, date_highlights in sorted(dates.items()):
                output.append(f"\n## {date}\n")
                for highlight in date_highlights:
                    book_title = highlight.book.title if highlight.book else "Unknown Book"
                    output.append(f"- **{book_title}**: {highlight.text}")
                    if highlight.note:
                        output.append(f"  - *Note: {highlight.note}*")
                    output.append("")

        else:  # no grouping
            output.append("\n## All Highlights\n")
            for highlight in highlights:
                book_title = highlight.book.title if highlight.book else "Unknown Book"
                output.append(f"- **{book_title}**: {highlight.text}")
                if highlight.note:
                    output.append(f"  - *Note: {highlight.note}*")
                output.append("")

        return "\n".join(output)

    def _export_json(self, highlights: list[Highlight]) -> str:
        """Export highlights as JSON."""
        import json

        data = {
            "generated_at": datetime.now().isoformat(),
            "total_highlights": len(highlights),
            "highlights": [],
        }

        for highlight in highlights:
            highlight_data = {
                "id": highlight.id,
                "text": highlight.text,
                "note": highlight.note,
                "highlighted_at": highlight.highlighted_at.isoformat()
                if highlight.highlighted_at
                else None,
                "updated": highlight.updated.isoformat() if highlight.updated else None,
                "url": highlight.url,
                "book": {
                    "id": highlight.book.id,
                    "title": highlight.book.title,
                    "author": highlight.book.author,
                    "source": highlight.book.source,
                }
                if highlight.book
                else None,
            }
            data["highlights"].append(highlight_data)

        return json.dumps(data, indent=2, ensure_ascii=False)

    def _export_csv(self, highlights: list[Highlight]) -> str:
        """Export highlights as CSV."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "id",
                "text",
                "note",
                "book_title",
                "book_author",
                "book_source",
                "highlighted_at",
                "updated",
                "url",
            ]
        )

        # Write data
        for highlight in highlights:
            writer.writerow(
                [
                    highlight.id,
                    highlight.text,
                    highlight.note,
                    highlight.book.title if highlight.book else "",
                    highlight.book.author if highlight.book else "",
                    highlight.book.source if highlight.book else "",
                    highlight.highlighted_at.isoformat() if highlight.highlighted_at else "",
                    highlight.updated.isoformat() if highlight.updated else "",
                    highlight.url or "",
                ]
            )

        return output.getvalue()

    def _export_txt(self, highlights: list[Highlight], group_by: str) -> str:
        """Export highlights as plain text."""
        output = ["Readwise Highlights Digest"]
        output.append("=" * 30)
        output.append(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"Total highlights: {len(highlights)}")
        output.append("")

        if group_by == "book":
            books = defaultdict(list)
            for highlight in highlights:
                book_title = highlight.book.title if highlight.book else "Unknown Book"
                books[book_title].append(highlight)

            for book_title, book_highlights in books.items():
                output.append(f"Book: {book_title}")
                output.append("-" * (len(book_title) + 6))
                for i, highlight in enumerate(book_highlights, 1):
                    output.append(f"{i}. {highlight.text}")
                    if highlight.note:
                        output.append(f"   Note: {highlight.note}")
                    output.append("")
                output.append("")

        else:
            for i, highlight in enumerate(highlights, 1):
                book_title = highlight.book.title if highlight.book else "Unknown Book"
                output.append(f"{i}. [{book_title}] {highlight.text}")
                if highlight.note:
                    output.append(f"   Note: {highlight.note}")
                output.append("")

        return "\n".join(output)
