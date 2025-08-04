# app/tasks/embed.py

import numpy as np
import os
import json
from dotenv import load_dotenv
from app.database import SessionLocal
from app.models import UserEmbedding

# Load environment variables
load_dotenv()

def generate_face_embedding(user_id, face_path, image_type="front"):
    """
    Generate a face embedding (currently using fake embeddings for POC).
    
    Args:
        user_id: The ID of the user
        face_path: Path to the face image
        image_type: Type of image ("front" or "side")
        
    Returns:
        True if embedding was successful, False otherwise
    """
    session = SessionLocal()
    
    try:
        # For POC: Generate a deterministic embedding based on user_id and face_path
        # In production, this would use InsightFace to generate real embeddings
        
        # Use a hash of the user_id and face_path as a seed for reproducibility
        import hashlib
        seed = int(hashlib.md5(f"{user_id}_{face_path}_{image_type}".encode()).hexdigest(), 16) % 10000
        np.random.seed(seed)
        
        # Generate a base embedding that will be consistent for the same user and image
        fake_embedding = np.random.rand(512).tolist()
        
        # Add a bias based on user_id to ensure different users have different embeddings
        # This creates a unique "signature" for each user
        for i in range(len(fake_embedding)):
            fake_embedding[i] = (fake_embedding[i] + (user_id * 0.1)) % 1.0
            
        # Normalize the embedding (as real embeddings would be normalized)
        norm = np.linalg.norm(fake_embedding)
        normalized_embedding = [x/norm for x in fake_embedding]
        
        # Convert embedding to JSON string for storage
        embedding_json = json.dumps(normalized_embedding)
        
        # Add image type to distinguish between front and side view embeddings
        embedding_type = f"face_{image_type}"
        
        # Save to DB
        new_emb = UserEmbedding(
            user_id=user_id, 
            embedding=embedding_json,
            embedding_type=embedding_type
        )
        session.add(new_emb)
        session.commit()
        
        print(f"Generated fake {image_type} embedding for user {user_id}")
        return True
        
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return False
        
    finally:
        session.close()

def generate_board_embedding(user_id, board_path):
    """
    Generate a surfboard embedding (currently using fake embeddings for POC).
    
    Args:
        user_id: The ID of the user
        board_path: Path to the surfboard image
        
    Returns:
        True if embedding was successful, False otherwise
    """
    # For POC, we'll just use the same fake embedding generation
    # In production, this would use a different model specialized for object recognition
    session = SessionLocal()
    
    try:
        # Generate a deterministic embedding based on user_id and board_path
        # In production, this would use a specialized model for object recognition
        
        # Use a hash of the user_id and board_path as a seed for reproducibility
        import hashlib
        seed = int(hashlib.md5(f"{user_id}_{board_path}_board".encode()).hexdigest(), 16) % 10000
        np.random.seed(seed)
        
        # Generate a base embedding that will be consistent for the same user and board
        fake_embedding = np.random.rand(512).tolist()
        
        # Add a bias based on user_id but with a different pattern than face embeddings
        # This creates a unique "signature" for each user's board
        for i in range(len(fake_embedding)):
            fake_embedding[i] = (fake_embedding[i] + (user_id * 0.15 + 0.2)) % 1.0
            
        # Normalize the embedding
        norm = np.linalg.norm(fake_embedding)
        normalized_embedding = [x/norm for x in fake_embedding]
        
        # Convert embedding to JSON string for storage
        embedding_json = json.dumps(normalized_embedding)
        
        # Set embedding type to 'board'
        embedding_type = 'board'
        
        # Save to DB
        new_emb = UserEmbedding(
            user_id=user_id, 
            embedding=embedding_json,
            embedding_type=embedding_type
        )
        session.add(new_emb)
        session.commit()
        
        print(f"Generated fake board embedding for user {user_id}")
        return True
        
    except Exception as e:
        print(f"Error generating board embedding: {str(e)}")
        return False
        
    finally:
        session.close()
