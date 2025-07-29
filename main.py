"""Example usage of the Readwise Digest SDK."""

from readwise_digest import (
    DigestService,
    HighlightPoller,
    PollingConfig,
    ReadwiseClient,
    setup_logging,
)


def main():
    """Demonstrate basic SDK usage."""
    # Set up logging
    setup_logging(level="INFO")

    # Create client
    client = ReadwiseClient()

    # Create digest service
    digest_service = DigestService(client)

    print("=== Readwise Digest SDK Demo ===")

    # Get recent highlights
    print("\n1. Getting recent highlights (last 24 hours)...")
    try:
        recent_highlights = digest_service.get_recent_highlights(hours=24)
        print(f"Found {len(recent_highlights)} recent highlights")

        if recent_highlights:
            # Show first few highlights
            for i, highlight in enumerate(recent_highlights[:3]):
                book_title = highlight.book.title if highlight.book else "Unknown Book"
                print(f"  {i+1}. [{book_title}] {highlight.text[:100]}...")

        # Export to markdown
        if recent_highlights:
            print("\n2. Exporting to markdown...")
            markdown = digest_service.export_digest(
                highlights=recent_highlights[:10],  # First 10
                format="markdown",
                group_by="book",
            )
            print("Markdown export created (first 500 chars):")
            print(markdown[:500] + "..." if len(markdown) > 500 else markdown)

    except Exception as e:
        print(f"Error getting highlights: {e}")

    # Demonstrate polling (single poll)
    print("\n3. Testing single poll operation...")
    try:
        config = PollingConfig(interval_seconds=300, lookback_hours=1, enable_persistence=False)

        poller = HighlightPoller(client, config)
        result = poller.poll_once()

        if result["success"]:
            print(f"Poll successful: {result['highlights_count']} highlights found")
        else:
            print(f"Poll failed: {result.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"Error during polling: {e}")

    print("\n=== Demo Complete ===")
    print("\nTo start continuous polling, run:")
    print("  python -m readwise_digest.cli poll --output-dir ./highlights")
    print("\nTo create a digest, run:")
    print("  python -m readwise_digest.cli digest --hours 24 --format markdown")


if __name__ == "__main__":
    main()
