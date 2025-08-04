# app/tasks/match.py
from celery import Celery
import os
import numpy as np
import cv2
import json
import hashlib
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
# We're not using face_app for the POC
# from app.tasks.embed import face_app
from app.models import SurferFrame, UserEmbedding
from app.database import SessionLocal

# Load environment variables
load_dotenv()

# Initialize Celery
BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("BROKER_URL"))
celery = Celery("match", broker=BROKER_URL)

# Matching threshold
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.8"))
# Lower threshold for board matching (fallback)
BOARD_MATCH_THRESHOLD = float(os.getenv("BOARD_MATCH_THRESHOLD", "0.7"))

def generate_fake_embedding(img, frame_path, user_id=0):
    """
    Generate a fake embedding for an image.
    This is a simplified version for the POC that doesn't require InsightFace.
    
    Args:
        img: The image to generate an embedding for
        frame_path: Path to the image file (used for deterministic generation)
        user_id: Optional user ID to bias the embedding (default: 0)
        
    Returns:
        A 512-dimensional numpy array representing the embedding
    """
    # Use a hash of the frame_path as a seed for reproducibility
    seed = int(hashlib.md5(f"{frame_path}".encode('utf-8')).hexdigest(), 16) % 10000
    np.random.seed(seed)
    
    # Generate a base embedding
    fake_embedding = np.random.rand(512)
    
    # Add a bias based on user_id if provided
    if user_id > 0:
        fake_embedding = (fake_embedding + (user_id * 0.1)) % 1.0
        
    # Normalize the embedding
    norm = np.linalg.norm(fake_embedding)
    normalized_embedding = fake_embedding / norm
    
    return normalized_embedding

def match_with_embedding_type(frame_embedding, user_embeddings, embedding_types):
    """
    Match a frame embedding with user embeddings of specific types.
    
    Args:
        frame_embedding: The embedding of the frame to match
        user_embeddings: List of UserEmbedding objects
        embedding_types: List of embedding types to consider (e.g., ['face_front', 'face_side'])
        
    Returns:
        Tuple of (user_id, score) for the best match, or None if no match found
    """
    best_match = None
    best_score = 0
    threshold = MATCH_THRESHOLD
    
    # If we're matching with board embeddings, use a lower threshold
    if embedding_types == ['board']:
        threshold = BOARD_MATCH_THRESHOLD
    
    # Filter embeddings by type
    filtered_embeddings = [emb for emb in user_embeddings if hasattr(emb, 'embedding_type') and emb.embedding_type in embedding_types]
    
    if not filtered_embeddings:
        print(f"No user embeddings found with types {embedding_types}")
        return None
    
    # Compare with filtered user embeddings
    for user_emb in filtered_embeddings:
        # Parse the stored embedding from JSON
        try:
            ref_embedding = np.array(json.loads(user_emb.embedding))
            
            # Calculate similarity
            score = cosine_similarity([frame_embedding], [ref_embedding])[0][0]
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = user_emb.user_id
        except Exception as e:
            print(f"Error comparing embeddings: {str(e)}")
            continue
    
    if best_match:
        return (best_match, best_score)
    else:
        return None

def match_surfer_to_users(frame_id):
    """
    Match a detected surfer frame to registered users using face and board embeddings.
    
    Args:
        frame_id: ID of the SurferFrame to match
        
    Returns:
        user_id of the matched user or 0 if no match found
    """
    session = SessionLocal()
    try:
        # Get the frame
        frame = session.query(SurferFrame).filter_by(id=frame_id).first()
        if not frame:
            print(f"Frame with ID {frame_id} not found")
            return 0
            
        # Read the image
        img = cv2.imread(frame.frame_path)
        if img is None:
            print(f"Could not read image at {frame.frame_path}")
            return 0
        
        # Generate a fake embedding for the frame
        frame_embedding = generate_fake_embedding(img, frame.frame_path)
        
        # Get all user embeddings
        user_embeddings = session.query(UserEmbedding).all()
        if not user_embeddings:
            print("No user embeddings found in database")
            return 0
        
        # First try matching with face embeddings (higher priority)
        face_match = match_with_embedding_type(frame_embedding, user_embeddings, ['face_front', 'face_side'])
        
        if face_match:
            user_id, score = face_match
            # Update the frame with the matched user_id
            frame.user_id = user_id
            frame.score = float(score)
            session.commit()
            print(f"Matched frame {frame_id} to user {user_id} with face score {score:.4f}")
            return user_id
            
        # If no face match, try board embeddings as fallback
        board_match = match_with_embedding_type(frame_embedding, user_embeddings, ['board'])
        
        if board_match:
            user_id, score = board_match
            # Update the frame with the matched user_id, but with a lower confidence
            frame.user_id = user_id
            frame.score = float(score * 0.8)  # Reduce confidence for board matches
            session.commit()
            print(f"Matched frame {frame_id} to user {user_id} with board score {score:.4f} (fallback)")
            return user_id
            
        # No match found
        print(f"No match found for frame {frame_id}")
        return 0
            
    except Exception as e:
        print(f"Error matching frame {frame_id}: {str(e)}")
        return 0
        
    finally:
        session.close()

@celery.task(name="match_all_frames")
def match_all_frames():
    """
    Match all unmatched frames (user_id=0) to registered users.
    
    Returns:
        Number of successfully matched frames
    """
    session = SessionLocal()
    try:
        # Get all unmatched frames
        unmatched_frames = session.query(SurferFrame).filter_by(user_id=0).all()
        print(f"Found {len(unmatched_frames)} unmatched frames")
        
        match_count = 0
        for frame in unmatched_frames:
            user_id = match_surfer_to_users(frame.id)
            if user_id > 0:
                match_count += 1
                
        return match_count
        
    except Exception as e:
        print(f"Error matching frames: {str(e)}")
        return 0
        
    finally:
        session.close()