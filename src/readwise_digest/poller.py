"""Background polling service for monitoring new Readwise highlights."""

import logging
import signal
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from .client import ReadwiseClient
from .digest import DigestService, DigestStats
from .exceptions import RateLimitError, ReadwiseError
from .models import Highlight


@dataclass
class PollingConfig:
    """Configuration for the polling service."""

    interval_seconds: int = 300  # 5 minutes default
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    lookback_hours: int = 1
    enable_persistence: bool = True
    state_file: str = "poller_state.json"
    log_level: str = "INFO"
    max_highlights_per_poll: int = 1000


class HighlightPoller:
    """Background service for polling Readwise API for new highlights."""

    def __init__(
        self,
        client: ReadwiseClient,
        config: Optional[PollingConfig] = None,
        on_new_highlights: Optional[Callable[[list[Highlight], DigestStats], None]] = None,
    ):
        self.client = client
        self.config = config or PollingConfig()
        self.digest_service = DigestService(client)
        self.on_new_highlights = on_new_highlights

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))

        # State management
        self.is_running = False
        self.last_poll_time: Optional[datetime] = None
        self.total_polls = 0
        self.total_highlights_found = 0
        self.error_count = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Load persistent state
        if self.config.enable_persistence:
            self._load_state()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start(self, daemon: bool = True) -> None:
        """Start the polling service in a background thread."""
        if self.is_running:
            self.logger.warning("Poller is already running")
            return

        self.logger.info(f"Starting highlight poller (interval: {self.config.interval_seconds}s)")
        self.is_running = True
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._poll_loop, daemon=daemon)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        """Stop the polling service gracefully."""
        if not self.is_running:
            return

        self.logger.info("Stopping highlight poller...")
        self.is_running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                self.logger.warning("Poller thread did not stop within timeout")

        if self.config.enable_persistence:
            self._save_state()

        self.logger.info("Highlight poller stopped")

    def poll_once(self) -> dict[str, Any]:
        """Perform a single poll operation and return results."""
        start_time = datetime.now()
        self.logger.info("Starting single poll operation")

        try:
            # Determine lookback time
            if self.last_poll_time:
                # Look back from last successful poll
                lookback_time = self.last_poll_time
            else:
                # First poll - look back configured hours
                lookback_time = start_time - timedelta(hours=self.config.lookback_hours)

            # Get recent highlights
            highlights = self.digest_service.get_recent_highlights(
                hours=int((start_time - lookback_time).total_seconds() / 3600),
                include_books=True,
            )

            # Limit highlights if needed
            if len(highlights) > self.config.max_highlights_per_poll:
                self.logger.warning(
                    f"Found {len(highlights)} highlights, limiting to {self.config.max_highlights_per_poll}",
                )
                highlights = highlights[: self.config.max_highlights_per_poll]

            # Create stats
            execution_time = (datetime.now() - start_time).total_seconds()
            stats = self.digest_service.create_digest_stats(
                highlights=highlights,
                time_range=f"Last poll to now ({lookback_time} to {start_time})",
                execution_time=execution_time,
            )

            # Update state
            self.last_poll_time = start_time
            self.total_polls += 1
            self.total_highlights_found += len(highlights)

            # Callback for new highlights
            if highlights and self.on_new_highlights:
                try:
                    self.on_new_highlights(highlights, stats)
                except Exception as e:
                    self.logger.error(f"Error in highlight callback: {e}")

            # Log results
            self.logger.info(
                f"Poll completed: {len(highlights)} highlights found in {execution_time:.2f}s",
            )

            return {
                "success": True,
                "highlights_count": len(highlights),
                "execution_time": execution_time,
                "lookback_time": lookback_time.isoformat(),
                "stats": stats,
            }

        except RateLimitError as e:
            self.logger.warning(f"Rate limited during poll: {e}")
            self.error_count += 1
            return {
                "success": False,
                "error": "rate_limit",
                "retry_after": getattr(e, "retry_after", 60),
                "message": str(e),
            }

        except ReadwiseError as e:
            self.logger.error(f"API error during poll: {e}")
            self.error_count += 1
            return {
                "success": False,
                "error": "api_error",
                "message": str(e),
            }

        except Exception as e:
            self.logger.error(f"Unexpected error during poll: {e}")
            self.error_count += 1
            return {
                "success": False,
                "error": "unexpected_error",
                "message": str(e),
            }

    def get_status(self) -> dict[str, Any]:
        """Get current status of the poller."""
        return {
            "is_running": self.is_running,
            "last_poll_time": self.last_poll_time.isoformat() if self.last_poll_time else None,
            "total_polls": self.total_polls,
            "total_highlights_found": self.total_highlights_found,
            "error_count": self.error_count,
            "config": {
                "interval_seconds": self.config.interval_seconds,
                "lookback_hours": self.config.lookback_hours,
                "max_retries": self.config.max_retries,
            },
        }

    def _poll_loop(self) -> None:
        """Main polling loop running in background thread."""
        retry_count = 0

        while self.is_running and not self._stop_event.is_set():
            try:
                result = self.poll_once()

                if result["success"]:
                    retry_count = 0  # Reset retry count on success

                    # Wait for next poll
                    if self._stop_event.wait(timeout=self.config.interval_seconds):
                        break  # Stop event was set

                else:
                    # Handle errors with backoff
                    retry_count += 1

                    if result.get("error") == "rate_limit":
                        # Special handling for rate limits
                        wait_time = result.get("retry_after", 60)
                        self.logger.info(f"Rate limited, waiting {wait_time} seconds")
                        if self._stop_event.wait(timeout=wait_time):
                            break

                    elif retry_count < self.config.max_retries:
                        # Exponential backoff for other errors
                        wait_time = min(
                            self.config.interval_seconds
                            * (self.config.retry_backoff_factor**retry_count),
                            300,  # Max 5 minutes
                        )
                        self.logger.info(
                            f"Retrying in {wait_time} seconds (attempt {retry_count}/{self.config.max_retries})"
                        )
                        if self._stop_event.wait(timeout=wait_time):
                            break

                    else:
                        # Max retries exceeded, wait for normal interval
                        self.logger.error("Max retries exceeded, waiting for next interval")
                        retry_count = 0
                        if self._stop_event.wait(timeout=self.config.interval_seconds):
                            break

            except Exception as e:
                self.logger.error(f"Unexpected error in poll loop: {e}")
                retry_count += 1

                if retry_count < self.config.max_retries:
                    wait_time = self.config.interval_seconds
                    if self._stop_event.wait(timeout=wait_time):
                        break
                else:
                    self.logger.error("Too many consecutive errors, stopping poller")
                    break

        self.is_running = False
        self.logger.info("Poll loop exited")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def _save_state(self) -> None:
        """Save poller state to disk."""
        import json

        try:
            state = {
                "last_poll_time": self.last_poll_time.isoformat() if self.last_poll_time else None,
                "total_polls": self.total_polls,
                "total_highlights_found": self.total_highlights_found,
                "error_count": self.error_count,
            }

            state_path = Path(self.config.state_file)
            with open(state_path, "w") as f:
                json.dump(state, f, indent=2)

            self.logger.debug(f"State saved to {state_path}")

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def _load_state(self) -> None:
        """Load poller state from disk."""
        import json

        try:
            state_path = Path(self.config.state_file)
            if not state_path.exists():
                return

            with open(state_path) as f:
                state = json.load(f)

            if state.get("last_poll_time"):
                self.last_poll_time = datetime.fromisoformat(state["last_poll_time"])

            self.total_polls = state.get("total_polls", 0)
            self.total_highlights_found = state.get("total_highlights_found", 0)
            self.error_count = state.get("error_count", 0)

            self.logger.debug(f"State loaded from {state_path}")

        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")


def create_simple_callback(
    output_dir: str = "./digests",
    format: str = "markdown",
) -> Callable[[list[Highlight], DigestStats], None]:
    """Create a simple callback that saves highlights to files."""

    def callback(highlights: list[Highlight], stats: DigestStats) -> None:
        if not highlights:
            return

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"highlights_{timestamp}.{format}"
        file_path = output_path / filename

        # Create digest service to export highlights
        from .digest import DigestService

        # We need a client for the digest service, but we only use it for exporting
        # so we can create a dummy one
        digest_service = DigestService(None)  # type: ignore

        try:
            content = digest_service.export_digest(highlights, format=format)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger = logging.getLogger(__name__)
            logger.info(
                f"Saved {len(highlights)} highlights to {file_path} "
                f"(execution time: {stats.execution_time:.2f}s)",
            )

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save highlights: {e}")

    return callback
