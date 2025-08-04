# update_paths.py
# -*- coding: utf-8 -*-
import sqlite3
import os

def update_frame_paths():
    # Connect to the database
    conn = sqlite3.connect('instance/seesea.sqlite')
    cursor = conn.cursor()
    
    # Get all records from surfer_frames
    cursor.execute('SELECT id, frame_path FROM surfer_frames')
    frames = cursor.fetchall()
    
    updated_count = 0
    
    # Update each record if needed
    for frame_id, frame_path in frames:
        if frame_path.startswith('app/static/'):
            # Remove the 'app/static/' prefix
            new_path = frame_path[len('app/static/'):]
            
            # Update the record
            cursor.execute('UPDATE surfer_frames SET frame_path = ? WHERE id = ?', (new_path, frame_id))
            updated_count += 1
    
    # Commit the changes
    conn.commit()
    
    # Close the connection
    conn.close()
    
    return updated_count

if __name__ == '__main__':
    print('Updating frame paths in the database...')
    updated_count = update_frame_paths()
    print(f'Updated {updated_count} records in the database.')
