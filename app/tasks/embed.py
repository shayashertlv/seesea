# app/tasks/embed.py

import numpy as np
import os
from app.database import SessionLocal
from app.models import UserEmbedding

def generate_face_embedding(user_id, face_path):
    """
    Fake embedding generation for now.
    We’ll replace this with real InsightFace embedding logic.
    """
    session = SessionLocal()

    # For now, generate a random 512-dimensional vector
    fake_embedding = np.random.rand(512).tolist()

    # Save to DB
    new_emb = UserEmbedding(user_id=user_id, embedding=str(fake_embedding))
    session.add(new_emb)
    session.commit()
    session.close()

    print(f"Generated fake embedding for user {user_id}")
