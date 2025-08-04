#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_postgres_video_paths():
    """
    Update video_path and thumbnail_path values in the SurfVideo table to:
    1. Remove 'app/static/' or 'app\\static\\' prefix
    2. Ensure all paths use forward slashes for web URLs
    """
    # Get database connection string from environment
    db_url = os.environ.get("DATABASE_URL")
    
    if not db_url:
        print("DATABASE_URL environment variable not found.")
        return
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check if the surf_videos table exists
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'surf_videos')")
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("The surf_videos table does not exist in the database.")
            return
        
        # Get all records from surf_videos
        cursor.execute("SELECT id, video_path, thumbnail_path FROM surf_videos")
        videos = cursor.fetchall()
        
        if not videos:
            print("No records found in surf_videos table.")
            return
            
        print(f"Found {len(videos)} videos in the database.")
        
        updated_count = 0
        
        # Update each record if needed
        for video_id, video_path, thumbnail_path in videos:
            video_updated = False
            thumbnail_updated = False
            new_video_path = video_path
            new_thumbnail_path = thumbnail_path
            
            # Process video_path
            if video_path:
                # Check for Windows-style path with backslashes
                if video_path.startswith('app\\static\\'):
                    new_video_path = video_path[len('app\\static\\'):]
                    video_updated = True
                # Check for Unix-style path with forward slashes
                elif video_path.startswith('app/static/'):
                    new_video_path = video_path[len('app/static/'):]
                    video_updated = True
                    
                # Convert all backslashes to forward slashes for web URLs
                if '\\' in new_video_path:
                    new_video_path = new_video_path.replace('\\', '/')
                    video_updated = True
            
            # Process thumbnail_path
            if thumbnail_path:
                # Check for Windows-style path with backslashes
                if thumbnail_path.startswith('app\\static\\'):
                    new_thumbnail_path = thumbnail_path[len('app\\static\\'):]
                    thumbnail_updated = True
                # Check for Unix-style path with forward slashes
                elif thumbnail_path.startswith('app/static/'):
                    new_thumbnail_path = thumbnail_path[len('app/static/'):]
                    thumbnail_updated = True
                    
                # Convert all backslashes to forward slashes for web URLs
                if '\\' in new_thumbnail_path:
                    new_thumbnail_path = new_thumbnail_path.replace('\\', '/')
                    thumbnail_updated = True
            
            # Update the record if needed
            if video_updated or thumbnail_updated:
                cursor.execute(
                    "UPDATE surf_videos SET video_path = %s, thumbnail_path = %s WHERE id = %s",
                    (new_video_path, new_thumbnail_path, video_id)
                )
                updated_count += 1
                print(f"Updated video ID {video_id}:")
                if video_updated:
                    print(f"  Video path: {video_path} -> {new_video_path}")
                if thumbnail_updated:
                    print(f"  Thumbnail path: {thumbnail_path} -> {new_thumbnail_path}")
        
        # Commit the changes
        conn.commit()
        
        # Print summary
        print(f"\nUpdated {updated_count} videos in the database.")
        
        # Verify the changes
        cursor.execute("SELECT id, video_path, thumbnail_path FROM surf_videos ORDER BY id DESC LIMIT 5")
        videos = cursor.fetchall()
        
        print("\nVerifying updated paths:")
        for video_id, video_path, thumbnail_path in videos:
            print(f"ID: {video_id}")
            print(f"  Video path: {video_path}")
            print(f"  Thumbnail path: {thumbnail_path}")
            
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error updating video paths in PostgreSQL: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()

if __name__ == "__main__":
    print("Updating video paths in the PostgreSQL database...")
    update_postgres_video_paths()
    print("Done.")