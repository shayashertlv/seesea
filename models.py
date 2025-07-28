from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String
from sqlalchemy.dialects.postgresql import ARRAY

Base = declarative_base()

class UserEmbedding(Base):
    __tablename__ = "user_embeddings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    embedding = Column(ARRAY(Float), nullable=False)

class SurferFrame(Base):
    __tablename__ = "surfer_frames"
    id = Column(Integer, primary_key=True)
    frame_path = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    x1, y1, x2, y2 = Column(Float), Column(Float), Column(Float), Column(Float)
    score = Column(Float, nullable=False)
