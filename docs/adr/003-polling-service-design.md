# ADR-003: Polling Service Design

## Status
Accepted

## Context
Users need a way to continuously monitor for new Readwise highlights without manually checking the API. This requires:
- Background processing capability
- Efficient polling with minimal API calls
- State persistence across restarts
- Graceful error handling and recovery
- Configurable polling intervals
- Callback system for processing new highlights

## Decision

### Architecture
We implement a `HighlightPoller` class with:

1. **Threading-based Background Execution**
   - Uses Python threading for background operation
   - Daemon threads for automatic cleanup
   - Signal handling for graceful shutdown

2. **Intelligent Polling Strategy**
   - Tracks last successful poll time
   - Only fetches highlights since last poll
   - Configurable lookback window for first run
   - Avoids duplicate processing

3. **State Persistence**
   - JSON-based state file storage
   - Automatic state saving on shutdown
   - State recovery on startup
   - Configurable state file location

4. **Callback System**
   - User-defined callback functions
   - Called with new highlights and statistics
   - Error isolation (callback errors don't stop polling)
   - Built-in simple file export callback

### Configuration

```python
@dataclass
class PollingConfig:
    interval_seconds: int = 300  # 5 minutes
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    lookback_hours: int = 1
    enable_persistence: bool = True
    state_file: str = "poller_state.json"
    log_level: str = "INFO"
    max_highlights_per_poll: int = 1000
```

### Usage Patterns

#### Simple Background Monitoring
```python
poller = HighlightPoller(client)
poller.start()  # Runs in background
```

#### With Custom Processing
```python
def process_highlights(highlights, stats):
    # Custom processing logic
    pass

poller = HighlightPoller(client, on_new_highlights=process_highlights)
poller.start()
```

#### One-time Poll
```python
result = poller.poll_once()
if result["success"]:
    print(f"Found {result['highlights_count']} new highlights")
```

### Error Handling Strategy

1. **Transient Errors**: Automatic retry with exponential backoff
2. **Rate Limiting**: Respect `Retry-After` headers
3. **Authentication Errors**: Log and continue (user intervention needed)
4. **Network Errors**: Retry with backoff
5. **Maximum Retries**: Fall back to next polling interval

### State Management

The poller maintains state including:
- Last successful poll timestamp
- Total polls completed
- Total highlights found
- Error counts
- Current configuration

State is automatically saved to disk and restored on startup.

### Memory and Performance

- **Streaming Processing**: Highlights processed as they arrive
- **Configurable Limits**: Maximum highlights per poll to prevent memory issues
- **Lazy Loading**: Books loaded on demand
- **Connection Reuse**: HTTP session maintained across polls

## Consequences

### Positive
- Automatic monitoring without user intervention
- Efficient API usage (only fetch new data)
- Resilient to errors and restarts
- Flexible processing via callbacks
- Low resource usage
- Observable via logging and status API

### Negative
- Threading complexity
- State file management
- Potential for missed highlights if state is lost
- Background resource usage

### Mitigations
- Comprehensive error handling and logging
- State file backup and recovery options
- Configurable resource limits
- Clear shutdown procedures
- Status monitoring capabilities

## Implementation Details

### Thread Safety
- All state modifications protected by appropriate locking
- Thread-safe communication via events
- Graceful shutdown coordination

### Signal Handling
- SIGINT and SIGTERM handlers for graceful shutdown
- State saving on shutdown
- Resource cleanup

### Monitoring and Observability
- Structured logging throughout
- Status API for current state
- Performance metrics in callbacks
- Error counting and reporting

## Alternatives Considered

1. **Async/await Design**: Rejected for complexity in simple use cases
2. **External Process**: Rejected to avoid deployment complexity
3. **Database State Storage**: Rejected to minimize dependencies
4. **Webhook-based**: Not supported by Readwise API

## Future Enhancements

1. **Async Support**: Could add async poller variant
2. **Multiple Callbacks**: Support for multiple callback functions
3. **Filtering**: Poll-time filtering to reduce processing
4. **Metrics Export**: Prometheus metrics endpoint
5. **Clustering**: Multiple poller coordination

## Notes
- Design favors simplicity and reliability over advanced features
- State persistence enables reliable long-running operation
- Callback system provides maximum flexibility for users
- Thread-based approach works well for I/O-bound polling operations