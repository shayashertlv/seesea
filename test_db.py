# test_db.py
# A simple script to test database operations with sample data

import os
import json
import numpy as np
from dotenv import load_dotenv
from app.database import SessionLocal, Base, engine
from app.models import User, UserEmbedding, SurferFrame, UserProfile, SurfVideo
from werkzeug.security import generate_password_hash
from datetime import datetime

# Load environment variables
load_dotenv()

def create_test_data():
    """Create sample data for testing database operations."""
    session = SessionLocal()
    
    try:
        # Check if tables exist, create them if not
        Base.metadata.create_all(bind=engine)
        print("Database tables created or verified.")
        
        # Create a test user if it doesn't exist
        test_user = session.query(User).filter_by(username="test_user").first()
        if not test_user:
            test_user = User(
                username="test_user",
                password=generate_password_hash("test_password")
            )
            session.add(test_user)
            session.commit()
            print(f"Created test user with ID: {test_user.id}")
        else:
            print(f"Test user already exists with ID: {test_user.id}")
        
        # Create test embeddings with different types
        embedding_types = ["face_front", "face_side"]
        
        for emb_type in embedding_types:
            # Check if embedding of this type already exists
            existing_emb = session.query(UserEmbedding).filter_by(
                user_id=test_user.id,
                embedding_type=emb_type
            ).first()
            
            if not existing_emb:
                # Generate a fake embedding
                fake_embedding = np.random.rand(512).tolist()
                
                # Add a bias based on embedding type
                bias = 0.1 if emb_type == "face_front" else 0.2
                for i in range(len(fake_embedding)):
                    fake_embedding[i] = (fake_embedding[i] + bias) % 1.0
                
                # Normalize the embedding
                norm = np.linalg.norm(fake_embedding)
                normalized_embedding = [x/norm for x in fake_embedding]
                
                # Convert to JSON string
                embedding_json = json.dumps(normalized_embedding)
                
                # Create the embedding
                new_emb = UserEmbedding(
                    user_id=test_user.id,
                    embedding=embedding_json,
                    embedding_type=emb_type
                )
                session.add(new_emb)
                session.commit()
                print(f"Created {emb_type} embedding for user {test_user.id}")
            else:
                print(f"{emb_type} embedding already exists for user {test_user.id}")
        
        # Create a test user profile if it doesn't exist
        test_profile = session.query(UserProfile).filter_by(user_id=test_user.id).first()
        if not test_profile:
            test_profile = UserProfile(
                user_id=test_user.id,
                face_image_path="uploads/test_face.jpg",
                face_side_image_path="uploads/test_face_side.jpg",
                wetsuit_description="Blue wetsuit with white stripes"
            )
            session.add(test_profile)
            session.commit()
            print(f"Created test profile for user {test_user.id}")
        else:
            print(f"Test profile already exists for user {test_user.id}")
        
        # Create a test surf video if it doesn't exist
        test_video = session.query(SurfVideo).filter_by(
            user_id=test_user.id,
            description="Test video"
        ).first()
        if not test_video:
            test_video = SurfVideo(
                user_id=test_user.id,
                video_path="uploads/test_video.mp4",
                thumbnail_path="uploads/test_thumbnail.jpg",
                location="Test Beach",
                description="Test video",
                duration=60.0,
                frame_count=1800,
                processed_frames=0,
                status="pending"
            )
            session.add(test_video)
            session.commit()
            print(f"Created test video for user {test_user.id}")
        else:
            print(f"Test video already exists for user {test_user.id}")
        
        # Create a test surfer frame if it doesn't exist
        test_frame = session.query(SurferFrame).filter_by(
            user_id=test_user.id,
            frame_path="captures/test_frame.jpg"
        ).first()
        if not test_frame:
            test_frame = SurferFrame(
                user_id=test_user.id,
                frame_path="captures/test_frame.jpg",
                x1=100.0,
                y1=100.0,
                x2=200.0,
                y2=200.0,
                score=0.9
            )
            session.add(test_frame)
            session.commit()
            print(f"Created test frame for user {test_user.id}")
        else:
            print(f"Test frame already exists for user {test_user.id}")
        
        print("Test data creation completed successfully.")
        
    except Exception as e:
        print(f"Error creating test data: {str(e)}")
        session.rollback()
    finally:
        session.close()

def test_queries():
    """Test various database queries."""
    session = SessionLocal()
    
    try:
        # Get the test user
        test_user = session.query(User).filter_by(username="test_user").first()
        if not test_user:
            print("Test user not found. Please run create_test_data() first.")
            return
        
        # Test query for embeddings by type
        for emb_type in ["face_front", "face_side"]:
            embeddings = session.query(UserEmbedding).filter_by(
                user_id=test_user.id,
                embedding_type=emb_type
            ).all()
            print(f"Found {len(embeddings)} {emb_type} embeddings for user {test_user.id}")
            
            # Test parsing the embedding
            if embeddings:
                embedding = embeddings[0]
                embedding_array = np.array(json.loads(embedding.embedding))
                print(f"  Embedding shape: {embedding_array.shape}")
                print(f"  Embedding norm: {np.linalg.norm(embedding_array):.4f}")
        
        # Test query for user profile
        profile = session.query(UserProfile).filter_by(user_id=test_user.id).first()
        if profile:
            print(f"Found profile for user {test_user.id}")
            print(f"  Face image: {profile.face_image_path}")
        else:
            print(f"No profile found for user {test_user.id}")
        
        # Test query for surf videos
        videos = session.query(SurfVideo).filter_by(user_id=test_user.id).all()
        print(f"Found {len(videos)} videos for user {test_user.id}")
        
        # Test query for surfer frames
        frames = session.query(SurferFrame).filter_by(user_id=test_user.id).all()
        print(f"Found {len(frames)} frames for user {test_user.id}")
        
        print("Query tests completed successfully.")
        
    except Exception as e:
        print(f"Error running query tests: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    print("Testing database operations...")
    create_test_data()
    print("\nTesting database queries...")
    test_queries()
    print("\nDatabase tests completed.")