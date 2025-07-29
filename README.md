# Readwise Digest

A comprehensive Python SDK for the Readwise API with polling and digest functionality.

## Features

- **Complete Readwise API Client**: Full support for highlights, books, and tags
- **Background Polling Service**: Automatically monitor for new highlights
- **Flexible Digest Creation**: Export highlights in multiple formats (Markdown, JSON, CSV, TXT)
- **Robust Error Handling**: Comprehensive error handling with automatic retries
- **Type Safety**: Full type hints throughout the codebase
- **Extensive Logging**: Configurable logging for monitoring and debugging
- **CLI Interface**: Command-line tools for common operations

## 🚀 Quick Start

### Prerequisites
- [uv](https://docs.astral.sh/uv/) - Python package manager
- [just](https://github.com/casey/just) - Command runner (optional but recommended)

### One-Command Setup
```bash
# Clone the repository
git clone <repository-url>
cd readwise-digest

# Quick setup (if you have just installed)
just quick-start

# OR manual setup
just setup
just env  # Edit .env with your API key
just sync
just serve
```

### Without Just
```bash
# Install dependencies
uv sync

# Create environment file
cp .env.example .env  # Edit with your API key

# Initialize database and sync
uv run python -c "from src.readwise_digest.database import init_db; init_db()"
uv run python sync_data.py

# Start the web server
uv run python server.py
```

## 🛠️ Just Commands

This project includes a comprehensive `justfile` with all common operations. Run `just --list` to see all available commands.

### Essential Commands
```bash
just setup          # Install dependencies and initialize database
just env             # Create .env file template
just sync            # Sync recent highlights (last 7 days)
just serve           # Start the web server
just status          # Show project status and stats
```

### Data Management
```bash
just sync-full       # Full synchronization of all data
just sync-recent     # Sync last 24 hours
just sync-history    # Show sync history
just db-stats        # Show database statistics
just backup          # Backup database
just export-json     # Export highlights to JSON
```

### Development
```bash
just test            # Run test suite
just test-cov        # Run tests with coverage
just format          # Format code with black/isort
just lint            # Lint code with flake8/mypy
just clean           # Clean up generated files
```

### CLI Tools
```bash
just latest          # Show your latest highlight
just metadata        # Show complete highlight metadata
just digest          # Create markdown digest
just poll            # Start background polling
just test-api        # Test API connection
```

### Health Checks
```bash
just check-api       # Verify API key and connection
just check-system    # Check system requirements
just git-status      # Show git status and recent commits
```

## Manual Setup (without Just)

### 1. Set up your API key

Create a `.env` file in your project directory:

```env
READWISE_API_KEY=your_api_key_here
```

### 2. Basic Usage

```python
from readwise_digest import ReadwiseClient, DigestService

# Create client
client = ReadwiseClient()

# Create digest service
digest = DigestService(client)

# Get recent highlights
highlights = digest.get_recent_highlights(hours=24)

# Export as markdown
markdown = digest.export_digest(highlights, format="markdown")
print(markdown)
```

### 3. Background Polling

```python
from readwise_digest import HighlightPoller, PollingConfig

def process_new_highlights(highlights, stats):
    print(f"Found {len(highlights)} new highlights!")
    for highlight in highlights:
        print(f"- {highlight.text}")

# Configure polling
config = PollingConfig(
    interval_seconds=300,  # 5 minutes
    lookback_hours=1
)

# Start polling
poller = HighlightPoller(client, config, on_new_highlights=process_new_highlights)
poller.start()

# Keep running...
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    poller.stop()
```

## Command Line Interface

### Test API Connection

```bash
python -m readwise_digest.cli test
```

### Create Digests

```bash
# Get highlights from last 24 hours
python -m readwise_digest.cli digest --hours 24 --format markdown

# Get all highlights with notes
python -m readwise_digest.cli digest --notes-only --format json -o highlights.json

# Get highlights from specific source
python -m readwise_digest.cli digest --source kindle --format csv
```

### Background Polling

```bash
# Start continuous polling (saves to files)
python -m readwise_digest.cli poll --output-dir ./highlights --interval 300

# Single poll operation
python -m readwise_digest.cli poll --once

# Custom configuration
python -m readwise_digest.cli poll --interval 600 --lookback 2 --format json
```

## API Reference

### ReadwiseClient

Main client for interacting with the Readwise API.

```python
client = ReadwiseClient(api_key="your_key")

# Get all highlights
highlights = list(client.get_highlights())

# Get highlights with filtering
highlights = list(client.get_highlights(
    updated_after="2023-01-01T00:00:00Z",
    book_id=123
))

# Get all books
books = list(client.get_books())

# Create new highlight
highlight = client.create_highlight(
    text="Important insight",
    title="My Book",
    author="Author Name",
    note="This is important because..."
)
```

### DigestService

High-level service for creating digests and processing highlights.

```python
digest = DigestService(client)

# Get recent highlights
highlights = digest.get_recent_highlights(hours=24)

# Get highlights with notes
noted = digest.get_highlights_with_notes()

# Get highlights by source
kindle_highlights = digest.get_highlights_by_source("kindle")

# Export in various formats
markdown = digest.export_digest(highlights, format="markdown", group_by="book")
json_data = digest.export_digest(highlights, format="json")
csv_data = digest.export_digest(highlights, format="csv")
```

### HighlightPoller

Background service for monitoring new highlights.

```python
from readwise_digest import HighlightPoller, PollingConfig

config = PollingConfig(
    interval_seconds=300,
    lookback_hours=1,
    max_retries=3,
    enable_persistence=True
)

poller = HighlightPoller(client, config, on_new_highlights=callback)

# Start/stop polling
poller.start()
poller.stop()

# Single poll
result = poller.poll_once()

# Get status
status = poller.get_status()
```

## Configuration

### Environment Variables

- `READWISE_API_KEY`: Your Readwise API key
- `READWISE_BASE_URL`: API base URL (default: https://readwise.io/api/v2)
- `READWISE_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `READWISE_LOG_FILE`: Log file path (optional)

### Polling Configuration

```python
config = PollingConfig(
    interval_seconds=300,      # Polling interval
    max_retries=3,            # Max retry attempts
    retry_backoff_factor=2.0, # Exponential backoff multiplier
    lookback_hours=1,         # Initial lookback window
    enable_persistence=True,   # Save state to disk
    state_file="poller_state.json",  # State file path
    log_level="INFO",         # Logging level
    max_highlights_per_poll=1000  # Limit highlights per poll
)
```

## Error Handling

The SDK provides comprehensive error handling:

```python
from readwise_digest import (
    ReadwiseError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ValidationError,
    ServerError
)

try:
    highlights = list(client.get_highlights())
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ReadwiseError as e:
    print(f"API error: {e}")
```

## Architecture Decision Records (ADRs)

Detailed architectural decisions are documented in `docs/adr/`:

- [001-architecture-overview.md](docs/adr/001-architecture-overview.md)
- [002-error-handling-strategy.md](docs/adr/002-error-handling-strategy.md)
- [003-polling-service-design.md](docs/adr/003-polling-service-design.md)

## Development

### Running Tests

```bash
# Install test dependencies
uv add --dev pytest pytest-cov responses

# Run tests
pytest

# Run with coverage
pytest --cov=src/readwise_digest
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/
```

### Project Structure

```
readwise-digest/
   src/readwise_digest/
      __init__.py          # Main exports
      client.py            # API client
      models.py            # Data models
      exceptions.py        # Custom exceptions
      digest.py            # Digest service
      poller.py            # Polling service
      logging_config.py    # Logging setup
      utils.py             # Utilities
      cli.py               # CLI interface
   tests/                   # Test suite
   docs/adr/               # Architecture decisions
   .env                    # Environment variables
   .gitignore             # Git ignore rules
   pyproject.toml         # Project configuration
```

## Examples

See `main.py` for a comprehensive example demonstrating SDK usage.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## Support

For questions or issues, please open an issue on GitHub.
