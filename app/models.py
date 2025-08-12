# app/models.py

from sqlalchemy import Column, Integer, Float, String, DateTime, Text, UniqueConstraint, Index
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
    embedding = Column(Text, nullable=False)  # Stored as a JSON string (face/outfit_color)
    embedding_type = Column(String(20), nullable=False)  # Allowed: face_front, face_side, outfit_color
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'embedding_type', name='uq_user_embedding_user_type'),
        Index('ix_user_embeddings_type', 'embedding_type'),
    )

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
    video_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    face_image_path = Column(String, nullable=False)
    face_side_image_path = Column(String, nullable=True)
    board_image_path = Column(String, nullable=True)  # Deprecated (unused): retained only for DB backward-compatibility; do not use
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
