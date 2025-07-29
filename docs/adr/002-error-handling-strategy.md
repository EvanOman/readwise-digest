# ADR-002: Error Handling Strategy

## Status
Accepted

## Context
The Readwise API can return various error conditions that need to be handled gracefully:
- Authentication failures (401)
- Rate limiting (429)
- Not found errors (404)
- Validation errors (400)
- Server errors (5xx)
- Network connectivity issues
- Timeout errors

We need a consistent strategy for handling these errors across the SDK.

## Decision

### Exception Hierarchy
We implement a custom exception hierarchy:

```python
ReadwiseError (base)
├── AuthenticationError (401)
├── RateLimitError (429) - includes retry_after
├── NotFoundError (404)
├── ValidationError (400)
└── ServerError (5xx)
```

### Error Handling Principles

1. **Specific Exception Types**: Each error condition gets its own exception type
2. **Rich Error Information**: Exceptions include status codes, response data, and context
3. **Automatic Retries**: Built-in retry logic for transient errors
4. **Rate Limit Respect**: Special handling for rate limits with backoff
5. **Graceful Degradation**: Continue operation when possible

### Implementation Details

#### ReadwiseClient Error Handling
- HTTP session configured with retry strategy
- Automatic retries for 429, 500, 502, 503, 504
- Exponential backoff with jitter
- Timeout configuration
- Connection pooling with limits

#### Polling Service Error Handling
- Separate retry logic with configurable backoff
- Persistent error counting
- Graceful shutdown on repeated failures
- State preservation across restarts

#### Digest Service Error Handling
- Error logging with context
- Partial success handling (some highlights fail)
- Resource cleanup on failures

### Retry Configuration

```python
# Default retry strategy
max_retries: 3
backoff_factor: 0.3
status_forcelist: [429, 500, 502, 503, 504]
allowed_methods: ["HEAD", "GET", "OPTIONS"]
```

### Rate Limiting Strategy

1. **Respect Retry-After**: Use server-provided retry delays
2. **Exponential Backoff**: For repeated rate limits
3. **Circuit Breaker**: Stop requests after repeated rate limits
4. **Logging**: Log rate limit occurrences for monitoring

## Consequences

### Positive
- Clear error semantics for users
- Automatic handling of transient errors
- Respectful API usage (rate limiting)
- Comprehensive error information for debugging
- Resilient to network issues

### Negative
- Increased complexity
- Potential for long delays during rate limiting
- Memory usage for retry state

### Mitigations
- Configurable retry parameters
- Maximum retry limits
- Timeout configurations
- Clear logging for troubleshooting

## Examples

### Basic Error Handling
```python
try:
    highlights = client.get_highlights()
except AuthenticationError:
    # Handle auth failure
    pass
except RateLimitError as e:
    # Wait and retry
    time.sleep(e.retry_after)
except ReadwiseError:
    # Handle other API errors
    pass
```

### Advanced Error Handling
```python
try:
    highlights = list(client.get_highlights())
except RateLimitError as e:
    logger.warning(f"Rate limited, retry after {e.retry_after}s")
    # Could implement custom backoff logic
except ServerError as e:
    logger.error(f"Server error {e.status_code}: {e.message}")
    # Could implement fallback data source
```

## Alternatives Considered

1. **Simple Exception Model**: Single exception type - rejected for lack of specificity
2. **No Automatic Retries**: Manual retry handling - rejected for poor user experience
3. **Async-only Error Handling**: Would complicate synchronous usage

## Notes
- Error handling is consistent across all SDK components
- Users can disable retries if needed for custom logic
- All errors include sufficient context for debugging
- The strategy balances automation with user control
