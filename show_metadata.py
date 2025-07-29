#!/usr/bin/env python3
"""Show all metadata available for highlights."""

import os
import json
from dotenv import load_dotenv
from readwise_digest import ReadwiseClient, DigestService
import sys

# Load environment variables
load_dotenv()

try:
    client = ReadwiseClient()
    digest = DigestService(client)
    
    # Get the most recent highlight
    recent_highlights = digest.get_recent_highlights(hours=24*7)  # Last week
    
    if recent_highlights:
        latest = recent_highlights[0]  # Most recent
        
        print("🔍 COMPLETE HIGHLIGHT METADATA")
        print("=" * 50)
        
        # Core highlight data
        print(f"📊 HIGHLIGHT DETAILS:")
        print(f"   ID: {latest.id}")
        print(f"   Text: {latest.text[:100]}{'...' if len(latest.text) > 100 else ''}")
        print(f"   Note: {latest.note if latest.note else 'None'}")
        print(f"   Location: {latest.location if latest.location else 'None'}")
        print(f"   Location Type: {latest.location_type.value if latest.location_type else 'None'}")
        print(f"   Color: {latest.color if latest.color else 'None'}")
        print(f"   URL: {latest.url if latest.url else 'None'}")
        print()
        
        # Timestamps
        print(f"📅 TIMESTAMPS:")
        print(f"   Highlighted At: {latest.highlighted_at if latest.highlighted_at else 'None'}")
        print(f"   Updated At: {latest.updated if latest.updated else 'None'}")
        print()
        
        # Book information
        print(f"📖 BOOK/SOURCE DETAILS:")
        if latest.book:
            print(f"   Book ID: {latest.book.id}")
            print(f"   Title: {latest.book.title}")
            print(f"   Author: {latest.book.author if latest.book.author else 'None'}")
            print(f"   Category: {latest.book.category if latest.book.category else 'None'}")
            print(f"   Source: {latest.book.source if latest.book.source else 'None'}")
            print(f"   Number of Highlights: {latest.book.num_highlights}")
            print(f"   Last Highlight At: {latest.book.last_highlight_at if latest.book.last_highlight_at else 'None'}")
            print(f"   Book Updated: {latest.book.updated if latest.book.updated else 'None'}")
            print(f"   Cover Image URL: {latest.book.cover_image_url if latest.book.cover_image_url else 'None'}")
            print(f"   Highlights URL: {latest.book.highlights_url if latest.book.highlights_url else 'None'}")
            print(f"   Source URL: {latest.book.source_url if latest.book.source_url else 'None'}")
            print(f"   ASIN: {latest.book.asin if latest.book.asin else 'None'}")
            
            # Book tags
            if latest.book.tags:
                print(f"   Book Tags: {[tag.name for tag in latest.book.tags]}")
            else:
                print(f"   Book Tags: None")
        else:
            print(f"   Book ID: {latest.book_id if latest.book_id else 'None'}")
            print(f"   Book Details: Not loaded")
        print()
        
        # Highlight tags
        print(f"🏷️  HIGHLIGHT TAGS:")
        if latest.tags:
            for tag in latest.tags:
                print(f"   - {tag.name} (ID: {tag.id})")
        else:
            print(f"   No tags")
        print()
        
        # Available location types
        print(f"📍 AVAILABLE LOCATION TYPES:")
        from readwise_digest.models import HighlightLocation
        for loc_type in HighlightLocation:
            print(f"   - {loc_type.value}")
        print()
        
        # Show raw JSON structure for reference
        print(f"🔧 RAW DATA STRUCTURE:")
        print("   Here's what the API returns (example structure):")
        example_structure = {
            "id": "highlight_id",
            "text": "highlight_text",
            "note": "optional_note",
            "location": "page_or_position_number",
            "location_type": "source_type",
            "highlighted_at": "2023-01-01T12:00:00Z",
            "updated": "2023-01-01T12:00:00Z",
            "book_id": "book_id",
            "url": "source_url",
            "color": "highlight_color",
            "tags": [{"id": 1, "name": "tag_name"}],
            "book": {
                "id": "book_id",
                "title": "book_title",
                "author": "book_author",
                "category": "books|articles|tweets|etc",
                "source": "kindle|instapaper|pocket|etc",
                "num_highlights": "total_highlights_in_book",
                "last_highlight_at": "2023-01-01T12:00:00Z",
                "updated": "2023-01-01T12:00:00Z",
                "cover_image_url": "cover_image_url",
                "highlights_url": "readwise_highlights_url",
                "source_url": "original_source_url",
                "asin": "amazon_asin",
                "tags": [{"id": 1, "name": "book_tag"}]
            }
        }
        print(json.dumps(example_structure, indent=2))
        
    else:
        print('No recent highlights found in the last week.')
        
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)