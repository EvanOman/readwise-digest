"""FastAPI routes for the Readwise Digest API."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from pydantic import BaseModel, Field

from ..database import get_session, Book, Highlight, Tag, SyncStatus
from ..database.database import get_db_stats
from ..database.sync import DatabaseSync
from ..client import ReadwiseClient
from ..logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Pydantic models for API responses
class BookResponse(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    num_highlights: int
    cover_image_url: Optional[str] = None
    source_url: Optional[str] = None
    last_highlight_at: Optional[datetime] = None
    updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TagResponse(BaseModel):
    id: int
    name: str
    highlight_count: int = 0
    book_count: int = 0
    
    class Config:
        from_attributes = True


class HighlightResponse(BaseModel):
    id: int
    text: str
    note: Optional[str] = None
    location: Optional[int] = None
    location_type: Optional[str] = None
    color: Optional[str] = None
    url: Optional[str] = None
    highlighted_at: Optional[datetime] = None
    updated: Optional[datetime] = None
    book: Optional[BookResponse] = None
    tags: List[TagResponse] = []
    
    class Config:
        from_attributes = True


class HighlightListResponse(BaseModel):
    highlights: List[HighlightResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class StatsResponse(BaseModel):
    books: int
    highlights: int
    tags: int
    sync_records: int
    last_sync: Optional[Dict[str, Any]] = None


class SyncResponse(BaseModel):
    sync_id: int
    status: str
    message: str


# API Routes
@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_session)):
    """Get database statistics."""
    try:
        stats = get_db_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/highlights", response_model=HighlightListResponse)
async def get_highlights(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    book_id: Optional[int] = Query(None, description="Filter by book ID"),
    source: Optional[str] = Query(None, description="Filter by source"),
    tag: Optional[str] = Query(None, description="Filter by tag name"),
    has_note: Optional[bool] = Query(None, description="Filter highlights with notes"),
    sort: str = Query("highlighted_at", description="Sort field"),
    order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_session)
):
    """Get paginated highlights with filtering and search."""
    try:
        # Base query
        query = db.query(Highlight)
        
        # Apply filters
        if search:
            # Search in text, note, book title, and author
            search_term = f"%{search}%"
            query = query.join(Book).filter(
                or_(
                    Highlight.text_search.ilike(search_term),
                    Highlight.text.ilike(search_term),
                    Highlight.note.ilike(search_term),
                    Book.title.ilike(search_term),
                    Book.author.ilike(search_term)
                )
            )
        
        if book_id:
            query = query.filter(Highlight.book_id == book_id)
        
        if source:
            query = query.join(Book).filter(Book.source == source)
        
        if tag:
            query = query.join(Highlight.tags).filter(Tag.name == tag)
        
        if has_note is not None:
            if has_note:
                query = query.filter(and_(Highlight.note.isnot(None), Highlight.note != ""))
            else:
                query = query.filter(or_(Highlight.note.is_(None), Highlight.note == ""))
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(Highlight, sort, Highlight.highlighted_at)
        if order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        offset = (page - 1) * per_page
        highlights = query.offset(offset).limit(per_page).all()
        
        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page
        
        return HighlightListResponse(
            highlights=[HighlightResponse.from_orm(h) for h in highlights],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error getting highlights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get highlights")


@router.get("/highlights/{highlight_id}", response_model=HighlightResponse)
async def get_highlight(highlight_id: int, db: Session = Depends(get_session)):
    """Get a specific highlight by ID."""
    try:
        highlight = db.query(Highlight).filter(Highlight.id == highlight_id).first()
        if not highlight:
            raise HTTPException(status_code=404, detail="Highlight not found")
        
        return HighlightResponse.from_orm(highlight)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting highlight {highlight_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get highlight")


@router.get("/books", response_model=List[BookResponse])
async def get_books(
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search in title and author"),
    source: Optional[str] = Query(None, description="Filter by source"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_session)
):
    """Get books with optional filtering."""
    try:
        query = db.query(Book)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Book.title.ilike(search_term),
                    Book.author.ilike(search_term)
                )
            )
        
        if source:
            query = query.filter(Book.source == source)
        
        if category:
            query = query.filter(Book.category == category)
        
        books = query.order_by(desc(Book.last_highlight_at)).limit(limit).all()
        
        return [BookResponse.from_orm(book) for book in books]
        
    except Exception as e:
        logger.error(f"Error getting books: {e}")
        raise HTTPException(status_code=500, detail="Failed to get books")


@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: Session = Depends(get_session)):
    """Get a specific book by ID."""
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        return BookResponse.from_orm(book)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get book")


@router.get("/books/{book_id}/highlights", response_model=List[HighlightResponse])
async def get_book_highlights(
    book_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_session)
):
    """Get all highlights for a specific book."""
    try:
        # Verify book exists
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        highlights = db.query(Highlight).filter(
            Highlight.book_id == book_id
        ).order_by(desc(Highlight.highlighted_at)).limit(limit).all()
        
        return [HighlightResponse.from_orm(h) for h in highlights]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting highlights for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get book highlights")


@router.get("/tags", response_model=List[TagResponse])
async def get_tags(
    limit: int = Query(100, ge=1, le=1000),
    min_count: int = Query(1, ge=1, description="Minimum highlight count"),
    db: Session = Depends(get_session)
):
    """Get tags with usage counts."""
    try:
        # Get tags with counts
        tags = db.query(
            Tag.id,
            Tag.name,
            func.count(Highlight.id).label('highlight_count')
        ).outerjoin(
            Highlight.tags
        ).group_by(
            Tag.id, Tag.name
        ).having(
            func.count(Highlight.id) >= min_count
        ).order_by(
            desc('highlight_count')
        ).limit(limit).all()
        
        return [
            TagResponse(
                id=tag.id,
                name=tag.name,
                highlight_count=tag.highlight_count,
                book_count=0  # TODO: Calculate book count
            )
            for tag in tags
        ]
        
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tags")


@router.get("/sources")
async def get_sources(db: Session = Depends(get_session)):
    """Get list of all sources with counts."""
    try:
        sources = db.query(
            Book.source,
            func.count(Book.id).label('book_count'),
            func.sum(Book.num_highlights).label('highlight_count')
        ).filter(
            Book.source.isnot(None)
        ).group_by(
            Book.source
        ).order_by(
            desc('highlight_count')
        ).all()
        
        return [
            {
                'name': source.source,
                'book_count': source.book_count,
                'highlight_count': source.highlight_count or 0
            }
            for source in sources
        ]
        
    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sources")


@router.post("/sync/full", response_model=SyncResponse)
async def sync_full(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force full sync regardless of last sync time")
):
    """Start a full synchronization with Readwise API."""
    try:
        client = ReadwiseClient()
        sync_service = DatabaseSync(client)
        
        def run_sync():
            try:
                result = sync_service.sync_all(force=force)
                logger.info(f"Full sync completed: {result}")
            except Exception as e:
                logger.error(f"Background sync failed: {e}")
        
        background_tasks.add_task(run_sync)
        
        return SyncResponse(
            sync_id=0,  # Will be updated by background task
            status="started",
            message="Full synchronization started in background"
        )
        
    except Exception as e:
        logger.error(f"Error starting sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to start synchronization")


@router.post("/sync/incremental", response_model=SyncResponse)
async def sync_incremental(
    background_tasks: BackgroundTasks,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """Start an incremental synchronization with Readwise API."""
    try:
        client = ReadwiseClient()
        sync_service = DatabaseSync(client)
        
        def run_sync():
            try:
                result = sync_service.sync_incremental(hours=hours)
                logger.info(f"Incremental sync completed: {result}")
            except Exception as e:
                logger.error(f"Background incremental sync failed: {e}")
        
        background_tasks.add_task(run_sync)
        
        return SyncResponse(
            sync_id=0,
            status="started",
            message=f"Incremental synchronization started (last {hours} hours)"
        )
        
    except Exception as e:
        logger.error(f"Error starting incremental sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to start incremental synchronization")


@router.get("/sync/history")
async def get_sync_history(
    limit: int = Query(10, ge=1, le=50)
):
    """Get recent synchronization history."""
    try:
        client = ReadwiseClient()
        sync_service = DatabaseSync(client)
        
        history = sync_service.get_sync_history(limit=limit)
        return history
        
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync history")


@router.get("/search")
async def search_highlights(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session)
):
    """Search highlights with full-text search."""
    try:
        search_term = f"%{q}%"
        
        highlights = db.query(Highlight).join(Book).filter(
            or_(
                Highlight.text_search.ilike(search_term),
                Highlight.text.ilike(search_term),
                Highlight.note.ilike(search_term),
                Book.title.ilike(search_term),
                Book.author.ilike(search_term)
            )
        ).order_by(
            desc(Highlight.highlighted_at)
        ).limit(limit).all()
        
        return {
            'query': q,
            'results': [HighlightResponse.from_orm(h) for h in highlights],
            'total': len(highlights)
        }
        
    except Exception as e:
        logger.error(f"Error searching highlights: {e}")
        raise HTTPException(status_code=500, detail="Search failed")