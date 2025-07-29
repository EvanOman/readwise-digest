#!/usr/bin/env python3
"""Sync data from Readwise API to local database."""

import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.readwise_digest import ReadwiseClient, setup_logging
from src.readwise_digest.database import init_db, DatabaseSync

# Setup logging
setup_logging(level="INFO")

async def main():
    print("🔄 Initializing database...")
    init_db()
    
    print("🔄 Creating Readwise client...")
    client = ReadwiseClient()
    
    print("🔄 Starting incremental sync (last 7 days)...")
    sync_service = DatabaseSync(client)
    
    try:
        result = sync_service.sync_incremental(hours=24*7)  # Last 7 days
        
        print(f"✅ Sync completed successfully!")
        print(f"   - Highlights synced: {result['highlights_synced']}")
        print(f"   - Books synced: {result['books_synced']}")
        print(f"   - Duration: {result['duration']:.2f} seconds")
        
        if result['errors']:
            print(f"⚠️  {len(result['errors'])} errors occurred:")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
    
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))