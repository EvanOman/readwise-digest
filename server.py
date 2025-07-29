#!/usr/bin/env python3
"""Development server for Readwise Digest web application."""

import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.readwise_digest.web.app import create_app
from src.readwise_digest.logging_config import setup_logging

# Setup logging
setup_logging(level="INFO")

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )