"""Command-line interface for Readwise Digest."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from . import (
    DigestService,
    HighlightPoller,
    PollingConfig,
    ReadwiseClient,
    get_logger,
    setup_logging,
)
from .exceptions import ReadwiseError

# Load environment variables from .env file
load_dotenv()


def create_client(api_key: Optional[str] = None) -> ReadwiseClient:
    """Create and return a configured ReadwiseClient."""
    try:
        return ReadwiseClient(api_key=api_key)
    except Exception as e:
        print(f"Error creating client: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_digest(args) -> None:
    """Handle digest command."""
    logger = get_logger(__name__)

    try:
        client = create_client(args.api_key)
        digest_service = DigestService(client)

        # Get highlights based on options
        if args.hours:
            logger.info(f"Getting highlights from last {args.hours} hours")
            highlights = digest_service.get_recent_highlights(
                hours=args.hours,
                include_books=True,
            )
        elif args.book_id:
            logger.info(f"Getting highlights for book {args.book_id}")
            highlights = digest_service.get_highlights_by_book(args.book_id)
        elif args.source:
            logger.info(f"Getting highlights from source {args.source}")
            highlights = digest_service.get_highlights_by_source(args.source)
        elif args.notes_only:
            logger.info("Getting highlights with notes only")
            highlights = digest_service.get_highlights_with_notes()
        else:
            logger.info("Getting all highlights")
            highlights = digest_service.get_all_highlights()

        if not highlights:
            print("No highlights found.")
            return

        # Export highlights
        output = digest_service.export_digest(
            highlights=highlights,
            format=args.format,
            group_by=args.group_by,
        )

        # Save or print output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)

            print(f"Digest saved to {output_path}")
        else:
            print(output)

        logger.info(f"Processed {len(highlights)} highlights")

    except ReadwiseError as e:
        print(f"Readwise API error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_poll(args) -> None:
    """Handle poll command."""
    logger = get_logger(__name__)

    try:
        client = create_client(args.api_key)

        # Create polling configuration
        config = PollingConfig(
            interval_seconds=args.interval,
            lookback_hours=args.lookback,
            max_retries=args.max_retries,
            enable_persistence=not args.no_state,
            state_file=args.state_file or "poller_state.json",
            log_level=args.log_level.upper(),
        )

        # Create callback for processing highlights
        def process_highlights(highlights, stats):
            logger.info(f"Found {len(highlights)} new highlights")

            if args.output_dir:
                # Save to file
                output_dir = Path(args.output_dir)
                output_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"highlights_{timestamp}.{args.format}"
                output_path = output_dir / filename

                digest_service = DigestService(client)
                content = digest_service.export_digest(
                    highlights=highlights,
                    format=args.format,
                )

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)

                logger.info(f"Saved highlights to {output_path}")
            else:
                # Print summary
                for highlight in highlights[:5]:  # Show first 5
                    book_title = highlight.book.title if highlight.book else "Unknown"
                    print(f"[{book_title}] {highlight.text[:100]}...")

                if len(highlights) > 5:
                    print(f"... and {len(highlights) - 5} more highlights")

        # Create and start poller
        poller = HighlightPoller(
            client=client,
            config=config,
            on_new_highlights=process_highlights,
        )

        if args.once:
            # Single poll
            result = poller.poll_once()
            if result["success"]:
                print(f"Poll completed: {result['highlights_count']} highlights found")
            else:
                print(f"Poll failed: {result['message']}", file=sys.stderr)
                sys.exit(1)
        else:
            # Continuous polling
            print(f"Starting poller (interval: {config.interval_seconds}s)")
            print("Press Ctrl+C to stop")

            try:
                poller.start(daemon=False)
                # Keep main thread alive
                import time

                while poller.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping poller...")
                poller.stop()

    except ReadwiseError as e:
        print(f"Readwise API error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_test(args) -> None:
    """Handle test command."""
    try:
        client = create_client(args.api_key)

        # Test API connection
        print("Testing API connection...")

        # Get a small number of highlights to test
        highlights = list(client.get_highlights())
        if highlights:
            print(f"✓ Successfully connected. Found {len(highlights)} highlights.")

            # Show first highlight as example
            highlight = highlights[0]
            book_title = highlight.book.title if highlight.book else "Unknown Book"
            print("\nExample highlight:")
            print(f"  Book: {book_title}")
            print(f"  Text: {highlight.text[:100]}{'...' if len(highlight.text) > 100 else ''}")
            if highlight.note:
                print(f"  Note: {highlight.note[:100]}{'...' if len(highlight.note) > 100 else ''}")
        else:
            print("✓ Connected successfully, but no highlights found.")

    except ReadwiseError as e:
        print(f"✗ API test failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Readwise Digest - A comprehensive Python SDK for the Readwise API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--api-key",
        help="Readwise API key (or set READWISE_API_KEY environment variable)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Digest command
    digest_parser = subparsers.add_parser(
        "digest",
        help="Create digest of highlights",
    )

    digest_parser.add_argument(
        "--hours",
        type=int,
        help="Get highlights from last N hours",
    )

    digest_parser.add_argument(
        "--book-id",
        type=int,
        help="Get highlights from specific book ID",
    )

    digest_parser.add_argument(
        "--source",
        help="Get highlights from specific source (e.g., kindle, twitter)",
    )

    digest_parser.add_argument(
        "--notes-only",
        action="store_true",
        help="Only include highlights with notes",
    )

    digest_parser.add_argument(
        "--format",
        choices=["markdown", "json", "csv", "txt"],
        default="markdown",
        help="Output format",
    )

    digest_parser.add_argument(
        "--group-by",
        choices=["book", "date", "source", "none"],
        default="book",
        help="How to group highlights",
    )

    digest_parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: print to stdout)",
    )

    # Poll command
    poll_parser = subparsers.add_parser(
        "poll",
        help="Poll for new highlights",
    )

    poll_parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Polling interval in seconds (default: 300)",
    )

    poll_parser.add_argument(
        "--lookback",
        type=int,
        default=1,
        help="Initial lookback hours (default: 1)",
    )

    poll_parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts (default: 3)",
    )

    poll_parser.add_argument(
        "--output-dir",
        help="Directory to save new highlights (default: print to stdout)",
    )

    poll_parser.add_argument(
        "--format",
        choices=["markdown", "json", "csv", "txt"],
        default="markdown",
        help="Output format for saved highlights",
    )

    poll_parser.add_argument(
        "--state-file",
        help="Path to state file (default: poller_state.json)",
    )

    poll_parser.add_argument(
        "--no-state",
        action="store_true",
        help="Disable state persistence",
    )

    poll_parser.add_argument(
        "--once",
        action="store_true",
        help="Run poll once and exit",
    )

    # Test command
    test_parser = subparsers.add_parser(
        "test",
        help="Test API connection",
    )

    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Set up logging
    setup_logging(level=args.log_level)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate command handler
    if args.command == "digest":
        cmd_digest(args)
    elif args.command == "poll":
        cmd_poll(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
