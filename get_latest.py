#!/usr/bin/env python3
"""Get the latest highlight from Readwise."""

import os
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
        book_title = latest.book.title if latest.book else 'Unknown Book'
        author = latest.book.author if latest.book and latest.book.author else 'Unknown Author'
        
        print(f'📖 Latest Highlight from: {book_title}')
        if author != 'Unknown Author':
            print(f'👤 Author: {author}')
        print(f'📅 Highlighted: {latest.highlighted_at.strftime("%Y-%m-%d %H:%M") if latest.highlighted_at else "Unknown date"}')
        print(f'💡 Source: {latest.book.source if latest.book and latest.book.source else "Unknown"}')
        print()
        print('"' + latest.text + '"')
        
        if latest.note:
            print()
            print(f'📝 Your note: {latest.note}')
    else:
        print('No recent highlights found in the last week.')
        
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)