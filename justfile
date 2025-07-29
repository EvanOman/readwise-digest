# Readwise Digest - Project Commands
# Run `just --list` to see all available commands

# Default recipe - shows help
default:
    @just --list

# Setup and Installation
# =====================

# Install all dependencies and set up the project
setup:
    @echo "🚀 Setting up Readwise Digest project..."
    @echo "📦 Installing Python dependencies with uv..."
    uv sync
    @echo "🗄️ Initializing database..."
    just init-db
    @echo "✅ Setup complete! Next steps:"
    @echo "   1. Add your API key: cp .env.example .env && edit .env"
    @echo "   2. Sync your data: just sync"
    @echo "   3. Start the server: just serve"

# Install Python dependencies
install:
    @echo "📦 Installing Python dependencies..."
    uv sync

# Create .env file from template
env:
    @if [ ! -f .env ]; then \
        echo "📝 Creating .env file..."; \
        echo "# Readwise API Configuration" > .env; \
        echo "READWISE_API_KEY=your_api_key_here" >> .env; \
        echo "READWISE_BASE_URL=https://readwise.io/api/v2" >> .env; \
        echo "" >> .env; \
        echo "# Polling Configuration" >> .env; \
        echo "POLL_INTERVAL_SECONDS=300" >> .env; \
        echo "MAX_RETRIES=3" >> .env; \
        echo "RETRY_BACKOFF_FACTOR=2" >> .env; \
        echo "" >> .env; \
        echo "# Logging Configuration" >> .env; \
        echo "LOG_LEVEL=INFO" >> .env; \
        echo "LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s" >> .env; \
        echo "✅ Created .env file. Please edit it with your Readwise API key."; \
    else \
        echo "⚠️  .env file already exists."; \
    fi

# Database Operations
# ==================

# Initialize the database (create tables)
init-db:
    @echo "🗄️ Initializing database..."
    uv run python -c "from src.readwise_digest.database import init_db; init_db(); print('✅ Database initialized')"

# Reset the database (WARNING: deletes all data)
reset-db:
    @echo "⚠️  WARNING: This will delete ALL data in the database!"
    @echo "Press Ctrl+C to cancel, or Enter to continue..."
    @read confirm
    uv run python -c "from src.readwise_digest.database.database import reset_db; reset_db(); print('✅ Database reset')"

# Show database statistics
db-stats:
    @echo "📊 Database Statistics:"
    uv run python -c "from src.readwise_digest.database.database import get_db_stats; import json; print(json.dumps(get_db_stats(), indent=2, default=str))"

# Data Synchronization
# ===================

# Sync recent highlights (last 7 days)
sync:
    @echo "🔄 Syncing recent highlights (last 7 days)..."
    uv run python sync_data.py

# Full synchronization of all data
sync-full:
    @echo "🔄 Starting full synchronization (this may take a while)..."
    uv run python -c "from src.readwise_digest import ReadwiseClient; from src.readwise_digest.database import DatabaseSync; client = ReadwiseClient(); sync = DatabaseSync(client); result = sync.sync_all(force=True); print(f'✅ Full sync completed: {result[\"highlights_synced\"]} highlights, {result[\"books_synced\"]} books')"

# Incremental sync (last 24 hours)
sync-recent:
    @echo "🔄 Syncing recent highlights (last 24 hours)..."
    uv run python -c "from src.readwise_digest import ReadwiseClient; from src.readwise_digest.database import DatabaseSync; client = ReadwiseClient(); sync = DatabaseSync(client); result = sync.sync_incremental(hours=24); print(f'✅ Incremental sync completed: {result[\"highlights_synced\"]} highlights')"

# Show sync history
sync-history:
    @echo "📜 Recent sync history:"
    uv run python -c "from src.readwise_digest import ReadwiseClient; from src.readwise_digest.database import DatabaseSync; client = ReadwiseClient(); sync = DatabaseSync(client); history = sync.get_sync_history(limit=5); [print(f'{h[\"started_at\"]} - {h[\"type\"]} sync: {h[\"highlights_synced\"]} highlights ({h[\"status\"]})')for h in history]"

# Development Server
# =================

# Start the web server (development mode)
serve:
    @echo "🌐 Starting Readwise Digest web server..."
    @echo "📱 Open http://localhost:8000 in your browser"
    @echo "📚 API docs available at http://localhost:8000/api/docs"
    uv run python server.py

# Start server in background
serve-bg:
    @echo "🌐 Starting web server in background..."
    uv run python server.py &
    @echo "✅ Server started at http://localhost:8000"

# Stop background server
stop:
    @echo "🛑 Stopping web server..."
    pkill -f "python server.py" || echo "No server process found"

# CLI Tools
# =========

# Show your latest highlight
latest:
    @echo "📖 Your latest highlight:"
    uv run python get_latest.py

# Show complete highlight metadata
metadata:
    @echo "🔍 Complete highlight metadata:"
    uv run python show_metadata.py

# Test API connection
test-api:
    @echo "🔌 Testing Readwise API connection..."
    uv run python -m readwise_digest.cli test

# Create a digest (last 24 hours, markdown format)
digest:
    @echo "📄 Creating highlights digest (last 24 hours)..."
    uv run python -m readwise_digest.cli digest --hours 24 --format markdown

# Create digest and save to file
digest-save:
    @echo "📄 Creating highlights digest and saving to digest.md..."
    uv run python -m readwise_digest.cli digest --hours 24 --format markdown -o digest.md
    @echo "✅ Digest saved to digest.md"

# Start background polling service
poll:
    @echo "🔄 Starting background polling service..."
    @echo "📁 Highlights will be saved to ./highlights/ directory"
    uv run python -m readwise_digest.cli poll --output-dir ./highlights --interval 300

# Development & Testing
# ====================

# Run all tests
test:
    @echo "🧪 Running tests..."
    uv run pytest tests/ -v

# Run tests with coverage
test-cov:
    @echo "🧪 Running tests with coverage..."
    uv run pytest tests/ -v --cov=src/readwise_digest --cov-report=html
    @echo "📊 Coverage report generated in htmlcov/index.html"

# Format code with ruff
format:
    @echo "🎨 Formatting code..."
    uv run ruff format src/ tests/

# Lint code with ruff
lint:
    @echo "🔍 Linting code..."
    uv run ruff check src/ tests/ --fix

# Type check with mypy
type-check:
    @echo "🔍 Type checking..."
    uv run mypy src/

# Run all code quality checks
check:
    @echo "🔍 Running all code quality checks..."
    just lint
    just test

# Run all code quality checks including type checking
check-strict:
    @echo "🔍 Running all code quality checks with type checking..."
    just lint
    just type-check
    just test

# Install pre-commit hooks
install-hooks:
    @echo "🔗 Installing pre-commit hooks..."
    uv run pre-commit install

# Run pre-commit on all files
pre-commit-all:
    @echo "🔍 Running pre-commit on all files..."
    uv run pre-commit run --all-files

# Clean up generated files
clean:
    @echo "🧹 Cleaning up..."
    rm -rf __pycache__ .pytest_cache .mypy_cache htmlcov .coverage
    find . -name "*.pyc" -delete
    find . -name "*.pyo" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Project Information
# ==================

# Show project status and information
status:
    @echo "📊 Readwise Digest Project Status"
    @echo "================================="
    @echo "📁 Project Directory: $(pwd)"
    @echo "🐍 Python: $(uv run python --version)"
    @echo "📦 UV: $(uv --version)"
    @echo ""
    @if [ -f .env ]; then echo "✅ Environment file exists"; else echo "❌ Environment file missing - run 'just env'"; fi
    @if [ -f readwise_digest.db ]; then echo "✅ Database exists"; else echo "❌ Database not initialized - run 'just init-db'"; fi
    @echo ""
    just db-stats

# Show help with examples
help:
    @echo "🚀 Readwise Digest - Quick Start Guide"
    @echo "====================================="
    @echo ""
    @echo "📋 First Time Setup:"
    @echo "   just setup        # Install everything and initialize"
    @echo "   just env          # Create .env file (edit with your API key)"
    @echo "   just sync         # Sync your highlights"
    @echo "   just serve        # Start the web app"
    @echo ""
    @echo "🔄 Daily Usage:"
    @echo "   just sync         # Sync recent highlights"
    @echo "   just serve        # Start web interface"
    @echo "   just latest       # See your latest highlight"
    @echo ""
    @echo "🛠️  Development:"
    @echo "   just test         # Run tests"
    @echo "   just format       # Format code"
    @echo "   just lint         # Lint code"
    @echo ""
    @echo "📚 More commands: just --list"

# Backup and Restore
# =================

# Backup database to timestamped file
backup:
    @echo "💾 Creating database backup..."
    @timestamp=$(date +"%Y%m%d_%H%M%S"); \
    cp readwise_digest.db "backup_readwise_digest_$timestamp.db"; \
    echo "✅ Database backed up to backup_readwise_digest_$timestamp.db"

# Export highlights to JSON file
export-json:
    @echo "📤 Exporting highlights to JSON..."
    @timestamp=$(date +"%Y%m%d_%H%M%S"); \
    uv run python -c "from src.readwise_digest.database.database import get_session_factory; from src.readwise_digest.database.models import Highlight; import json; SessionLocal = get_session_factory(); session = SessionLocal(); highlights = session.query(Highlight).all(); data = [{'id': h.id, 'text': h.text, 'note': h.note, 'book_title': h.book.title if h.book else None, 'highlighted_at': h.highlighted_at.isoformat() if h.highlighted_at else None} for h in highlights]; json.dump(data, open(f'highlights_export_$timestamp.json', 'w'), indent=2); session.close(); print(f'✅ Exported {len(data)} highlights to highlights_export_$timestamp.json')"

# Health Checks
# ============

# Check if API key is configured and working
check-api:
    @echo "🔌 Checking API configuration..."
    @if [ -f .env ]; then \
        if grep -q "your_api_key_here" .env; then \
            echo "❌ API key not configured. Edit .env file with your Readwise API key."; \
        else \
            echo "✅ API key configured. Testing connection..."; \
            just test-api; \
        fi; \
    else \
        echo "❌ .env file not found. Run 'just env' to create it."; \
    fi

# Check system requirements
check-system:
    @echo "🔍 Checking system requirements..."
    @echo "UV Package Manager: $(uv --version 2>/dev/null || echo 'Not installed')"
    @echo "Python: $(python3 --version 2>/dev/null || echo 'Not found')"
    @echo "Just: $(just --version 2>/dev/null || echo 'Not installed')"
    @echo "Git: $(git --version 2>/dev/null || echo 'Not installed')"

# One-command project initialization
quick-start:
    @echo "🚀 Quick Start - Setting up Readwise Digest..."
    just setup
    just env
    @echo ""
    @echo "🎉 Setup complete! Next steps:"
    @echo "   1. Edit .env file with your Readwise API key"
    @echo "   2. Run 'just check-api' to test your API key"
    @echo "   3. Run 'just sync' to sync your highlights"
    @echo "   4. Run 'just serve' to start the web app"
    @echo ""
    @echo "💡 Tip: Run 'just help' for more commands"

# Show current git status and recent commits
git-status:
    @echo "📝 Git Status:"
    git status --short
    @echo ""
    @echo "📚 Recent commits:"
    git log --oneline -5

# Create a new git commit with all changes
commit message="Update project":
    @echo "📝 Creating git commit..."
    git add -A
    git commit -m "{{message}}"
    @echo "✅ Committed: {{message}}"
