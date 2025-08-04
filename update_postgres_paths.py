#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_postgres_paths():
    """
    Update frame_path values in the PostgreSQL database to:
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
        
        # Get all records from surfer_frames
        cursor.execute("SELECT id, frame_path FROM surfer_frames")
        frames = cursor.fetchall()
        
        updated_count = 0
        
        # Update each record if needed
        for frame_id, frame_path in frames:
            needs_update = False
            new_path = frame_path
            
            # Check for Windows-style path with backslashes
            if frame_path.startswith('app\\static\\'):
                new_path = frame_path[len('app\\static\\'):]
                needs_update = True
            # Check for Unix-style path with forward slashes
            elif frame_path.startswith('app/static/'):
                new_path = frame_path[len('app/static/'):]
                needs_update = True
                
            # Convert all backslashes to forward slashes for web URLs
            if '\\' in new_path:
                new_path = new_path.replace('\\', '/')
                needs_update = True
                
            # Update the record if needed
            if needs_update:
                cursor.execute("UPDATE surfer_frames SET frame_path = %s WHERE id = %s", (new_path, frame_id))
                updated_count += 1
        
        # Commit the changes
        conn.commit()
        
        # Print summary
        print(f"Updated {updated_count} records in the database.")
        
        # Verify the changes
        cursor.execute("SELECT id, frame_path FROM surfer_frames ORDER BY id DESC LIMIT 10")
        frames = cursor.fetchall()
        
        print("\nVerifying updated paths:")
        for frame_id, frame_path in frames:
            print(f"ID: {frame_id}, Path: {frame_path}")
            
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error updating paths in PostgreSQL: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()

if __name__ == "__main__":
    print("Updating frame paths in the PostgreSQL database...")
    update_postgres_paths()
    print("Done.")