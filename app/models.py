# app/models.py

from sqlalchemy import Column, Integer, Float, String
from app.database import Base
from flask_login import UserMixin

class User(Base, UserMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)


class UserEmbedding(Base):
    __tablename__ = "user_embeddings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    embedding = Column(String, nullable=False)  # Stored as a JSON string or delimited string

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
