# app/tasks/process_video.py

import os
import cv2
import time
from celery import shared_task
from app.database import SessionLocal
from app.models import SurfVideo, SurferFrame
from app.tasks.detect import detect_and_capture
from app.tasks.match import match_surfer_to_users, _resolve_image_path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@shared_task(name="process_video")
def process_video(video_id):
    """
    Process a video by detecting surfers and matching them to users.
    
    Args:
        video_id: ID of the SurfVideo to process
        
    Returns:
        True if processing was successful, False otherwise
    """
    session = SessionLocal()
    
    try:
        print(f"[task] process_video started for video_id={video_id}")
        # Get the video
        video = session.query(SurfVideo).filter_by(id=video_id).first()
        if not video:
            print(f"Video with ID {video_id} not found")
            return False
            
        # Update status to processing
        video.status = "processing"
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Failed to set video {video_id} to processing: {e}")
            try:
                video.status = "failed"
                session.commit()
            except Exception as e2:
                session.rollback()
                print(f"Also failed to mark video {video_id} failed: {e2}")
            return False
        
        # Open the video (resolve relative path under app/static if needed)
        video_path_resolved = _resolve_image_path(video.video_path)
        cap = cv2.VideoCapture(video_path_resolved)
        if not cap.isOpened():
            print(f"Could not open video at {video_path_resolved}")
            video.status = "failed"
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"Failed to mark video {video_id} as failed after open error: {e}")
            return False
            
        # Get video properties
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Create directory for frames
        frames_dir_full = os.path.join("app", "static", "frames", f"video_{video_id}")
        frames_dir_relative = os.path.join("frames", f"video_{video_id}")
        os.makedirs(frames_dir_full, exist_ok=True)
        
        # Process frames
        processed_frames = 0
        detected_frames = 0
        
        # Load the YOLO model once outside the loop for efficiency
        from app.tasks.detect import WEIGHTS_PATH, CONFIDENCE_THRESHOLD
        from ultralytics import YOLO
        
        print(f"Loading YOLO model from {WEIGHTS_PATH}...")
        model = YOLO(WEIGHTS_PATH)
        print("YOLO model loaded successfully")
        
        # For POC, process every 10th frame to speed things up
        frame_interval = 10
        
        for frame_idx in range(0, frame_count, frame_interval):
            # Set the frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                break
                
            # Save the frame
            frame_path_full = os.path.join(frames_dir_full, f"frame_{frame_idx}.jpg")
            cv2.imwrite(frame_path_full, frame)
            
            # Detect surfers in the frame using the YOLO model
            # Run detection on the frame
            try:
                results = model(frame)[0]
            except Exception as e:
                print(f"Error during model inference on frame {frame_idx}: {str(e)}")
                continue
            frame_detections = 0
            
            # Process each detection
            for i, box in enumerate(results.boxes):
                conf = float(box.conf)
                if conf < CONFIDENCE_THRESHOLD:
                    continue
                    
                # Get bounding box coordinates
                x1, y1, x2, y2 = map(float, box.xyxy[0])
                label = results.names[int(box.cls[0])]
                
                # Create a cropped image of the detection
                crop_filename = f"frame_{frame_idx}_detection_{i}.jpg"
                crop_path_full = os.path.join(frames_dir_full, crop_filename)
                crop_path_relative = os.path.join(frames_dir_relative, crop_filename)
                crop = frame[int(y1):int(y2), int(x1):int(x2)]
                cv2.imwrite(crop_path_full, crop)
                
                # Create a SurferFrame entry
                new_frame = SurferFrame(
                    user_id=0,  # Placeholder, will be updated by matching process
                    frame_path=crop_path_relative,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    score=conf,
                    video_id=video.id,
                )
                session.add(new_frame)
                frame_detections += 1
                
            # Commit all detections for this frame
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"Commit failed after adding detections for frame {frame_idx}: {e}")
                continue
            detected_frames += frame_detections
            
            # Print progress
            if frame_detections > 0:
                print(f"Frame {frame_idx}: Detected {frame_detections} surfers")
            
            # Update progress
            processed_frames += 1
            if processed_frames % 5 == 0:
                video.processed_frames = processed_frames
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"Failed to commit progress for video {video_id} at frame {frame_idx}: {e}")
                
            # Simulate processing time
            time.sleep(0.1)
        
        # Close the video
        cap.release()
        
        # Match detected surfers to users
        print(f"Processing complete. Matching {detected_frames} detected surfers to registered users...")
        
        try:
            # Import the matching function
            from app.tasks.match import match_all_frames
            
            # Run the matching process
            matched_count = match_all_frames()
            
            print(f"Matching complete. Successfully matched {matched_count} surfers to registered users.")
            
            # Update status to completed
            video.status = "completed"
            video.processed_frames = processed_frames
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"Failed to mark video {video_id} as completed: {e}")
            
        except Exception as e:
            print(f"Error during matching process: {str(e)}")
            video.status = "completed_with_errors"
            try:
                session.commit()
            except Exception as e2:
                session.rollback()
                print(f"Failed to mark video {video_id} as completed_with_errors: {e2}")
        
        print(f"Video processing completed: {processed_frames} frames processed, {detected_frames} surfers detected")
        return True
        
    except Exception as e:
        print(f"Error processing video {video_id}: {str(e)}")
        # Reset transaction and update status to failed
        try:
            session.rollback()
        except Exception:
            pass
        if 'video' in locals():
            video.status = "failed"
            try:
                session.commit()
            except Exception as e2:
                session.rollback()
                print(f"Also failed to mark video {video_id} as failed in outer except: {e2}")
        return False
        
    finally:
        session.close()

# Function to simulate a background task
def process_video_task():
    """
    Simulate a background task that processes pending videos.
    In production, this would be a Celery task.
    """
    session = SessionLocal()
    
    try:
        # Get pending videos
        pending_videos = session.query(SurfVideo).filter_by(status="pending").all()
        
        for video in pending_videos:
            print(f"Processing video {video.id}")
            process_video(video.id)
            
    except Exception as e:
        print(f"Error in process_video_task: {str(e)}")
        
    finally:
        session.close()

if __name__ == "__main__":
    # This allows running the script directly for testing
    process_video_task()