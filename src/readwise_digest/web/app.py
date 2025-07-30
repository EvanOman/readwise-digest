"""FastAPI application setup for Readwise Digest web interface."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..database import init_db
from ..logging_config import get_logger
from .api import router as api_router

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Readwise Digest",
        description="Browse and search your Readwise highlights",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Svelte dev server
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api")

    # Setup static file serving for the web app
    webapp_dir = Path(__file__).parent.parent.parent.parent / "webapp"
    webapp_dist_dir = webapp_dir / "dist"
    
    # Check for built webapp first, then fall back to raw HTML
    if webapp_dist_dir.exists():
        app.mount("/static", StaticFiles(directory=str(webapp_dist_dir / "assets")), name="static")
        index_file = webapp_dist_dir / "index.html"
    else:
        # Use the raw HTML file if no build directory exists
        index_file = webapp_dir / "index.html"
    
    if index_file.exists():
        @app.get("/")
        async def serve_app():
            """Serve the main application."""
            return FileResponse(str(index_file))

        @app.get("/{path:path}")
        async def serve_app_routes(path: str):
            """Serve the application for client-side routing."""
            # Check if it's an API route
            if path.startswith("api/"):
                return {"error": "API route not found"}

            # For any other route, serve the main app (SPA routing)
            return FileResponse(str(index_file))

    @app.on_event("startup")
    async def startup_event():
        """Initialize the application."""
        logger.info("Starting Readwise Digest web application")

        # Initialize database
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Shutting down Readwise Digest web application")

    return app
