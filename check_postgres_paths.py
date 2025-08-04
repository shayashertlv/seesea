#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_postgres_paths():
    """
    Check the current state of frame_path values in the PostgreSQL database.
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
        
        # Check surfer_frames table
        print("Checking surfer_frames table...")
        cursor.execute("SELECT id, frame_path FROM surfer_frames ORDER BY id DESC LIMIT 10")
        frames = cursor.fetchall()
        
        if not frames:
            print("No records found in surfer_frames table.")
        else:
            print(f"Found {len(frames)} records:")
            for frame_id, frame_path in frames:
                print(f"ID: {frame_id}, Path: {frame_path}")
                
            # Count paths with app/static/ prefix
            cursor.execute("SELECT COUNT(*) FROM surfer_frames WHERE frame_path LIKE 'app/static/%'")
            count = cursor.fetchone()[0]
            print(f"\nPaths with 'app/static/' prefix: {count}")
            
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {str(e)}")

if __name__ == "__main__":
    check_postgres_paths()