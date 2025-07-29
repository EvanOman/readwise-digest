# ADR-001: Architecture Overview

## Status
Accepted

## Context
We need to build a comprehensive Python SDK for the Readwise API that can:
1. Provide a clean, intuitive interface for API operations
2. Support background polling for new highlights
3. Offer digest functionality for processing and exporting highlights
4. Handle errors gracefully and provide robust retry mechanisms
5. Be easily extensible and maintainable

## Decision
We will implement a modular architecture with the following components:

### Core Components

1. **ReadwiseClient** (`client.py`)
   - Main API client with authentication
   - HTTP session management with retries
   - Rate limiting and error handling
   - CRUD operations for highlights, books, and tags

2. **Data Models** (`models.py`)
   - Dataclasses for Highlight, Book, and Tag entities
   - Type-safe representations of API responses
   - Built-in parsing from API JSON responses

3. **Custom Exceptions** (`exceptions.py`)
   - Specific exception types for different error conditions
   - Enhanced error information including status codes and responses

4. **DigestService** (`digest.py`)
   - High-level operations for retrieving and processing highlights
   - Multiple export formats (Markdown, JSON, CSV, TXT)
   - Flexible grouping and filtering options
   - Statistics generation

5. **HighlightPoller** (`poller.py`)
   - Background polling service with configurable intervals
   - Persistent state management
   - Graceful shutdown handling
   - Callback system for processing new highlights

### Design Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Type Safety**: Comprehensive type hints throughout the codebase
3. **Error Handling**: Robust error handling with specific exception types
4. **Configurability**: Extensive configuration options for different use cases
5. **Extensibility**: Clean interfaces that allow for easy extension
6. **Observability**: Comprehensive logging throughout the system

### Data Flow

```
ReadwiseClient → DigestService → HighlightPoller
     ↓               ↓               ↓
  Raw API      Processed Data   Background
  Operations   & Export         Monitoring
```

## Consequences

### Positive
- Clean separation makes testing easier
- Modular design allows users to use only what they need
- Comprehensive error handling improves reliability
- Type safety reduces runtime errors
- Background polling enables real-time monitoring

### Negative
- More complex than a single-file solution
- Requires understanding of multiple components
- Potential for over-engineering simple use cases

### Mitigations
- Clear documentation and examples
- Simple import structure via `__init__.py`
- Sensible defaults for all configurations
- Progressive complexity (simple → advanced use cases)

## Alternatives Considered

1. **Single-file SDK**: Rejected due to maintainability concerns
2. **Async-only approach**: Rejected to maintain simplicity for basic use cases
3. **External polling service**: Rejected to keep dependencies minimal

## Notes
- The architecture supports both synchronous and simple usage patterns
- Future extensions could include async support via separate modules
- The design is influenced by popular Python SDKs like boto3 and requests
