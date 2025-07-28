# tasks/match.py
from celery import Celery
import os
import numpy as np
import cv2
from sklearn.metrics.pairwise import cosine_similarity
from tasks.detect import detect
from tasks.preprocess import embed_image
from models import SurferFrame, UserEmbedding, Base  # absolute import of ORM models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Initialize Celery & DB
BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("BROKER_URL"))
celery = Celery("match", broker=BROKER_URL)

# Initialize database session
engine = create_engine(os.getenv("DATABASE_URL"))
Session = sessionmaker(bind=engine)

# Matching threshold
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.8"))

@celery.task(name="match", queue="match")
def match(frame_path: str):
    """
    Detects surfers in `frame_path`, embeds each box, compares to user refs, and writes hits.
    Returns list of (user_id, box, score) on match.
    """
    # 1. Run detection
    boxes = detect(frame_path)
    matches = []
    session = Session()

    # 2. Process each detection
    img = cv2.imread(frame_path)
    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        crop = img[y1:y2, x1:x2]
        tmp_path = "/tmp/crop.jpg"
        cv2.imwrite(tmp_path, crop)

        # 3. Embed the crop
        emb_path = embed_image(tmp_path)
        emb = np.load(emb_path)

        # 4. Compare to each reference embedding
        for ref in session.query(UserEmbedding).all():
            score = cosine_similarity([emb], [ref.embedding])[0][0]
            if score >= MATCH_THRESHOLD:
                matches.append((ref.user_id, box, float(score)))

    # 5. Persist matches
    for user_id, box, score in matches:
        sf = SurferFrame(
            frame_path=frame_path,
            user_id=user_id,
            x1=box[0], y1=box[1], x2=box[2], y2=box[3],
            score=score
        )
        session.add(sf)
    session.commit()
    session.close()
    return matches
