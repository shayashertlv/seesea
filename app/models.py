# app/models.py

from sqlalchemy import Column, Integer, Float, String, DateTime
from app.database import Base
from flask_login import UserMixin
from datetime import datetime

class User(Base, UserMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)


class UserEmbedding(Base):
    __tablename__ = "user_embeddings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    embedding = Column(String, nullable=False)  # Stored as a JSON string
    embedding_type = Column(String(20), nullable=False)  # face_front, face_side, board
    created_at = Column(DateTime, default=datetime.utcnow)

class SurferFrame(Base):
    __tablename__ = "surfer_frames"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    frame_path = Column(String, nullable=False)
    x1 = Column(Float)
    y1 = Column(Float)
    x2 = Column(Float)
    y2 = Column(Float)
    score = Column(Float)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    face_image_path = Column(String, nullable=False)
    face_side_image_path = Column(String, nullable=True)
    board_image_path = Column(String, nullable=False)
    wetsuit_description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SurfVideo(Base):
    __tablename__ = "surf_videos"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # User who uploaded the video
    video_path = Column(String, nullable=False)  # Path to the video file
    thumbnail_path = Column(String, nullable=True)  # Path to video thumbnail
    location = Column(String, nullable=True)  # Beach location
    description = Column(String, nullable=True)  # Video description
    duration = Column(Float, nullable=True)  # Video duration in seconds
    frame_count = Column(Integer, nullable=True)  # Total number of frames
    processed_frames = Column(Integer, default=0)  # Number of processed frames
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
