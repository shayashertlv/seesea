# tasks/preprocess.py
import os
import cv2
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from celery import Celery
import redis
import psycopg2
import torchreid
from torchvision.transforms import Compose, Resize, ToTensor
from PIL import Image

# ── load .env from project root ───────────────────────────
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

# ── Celery + storage clients ──────────────────────────────
celery_app = Celery(__name__, broker=os.getenv("BROKER_URL"))
r = redis.from_url(os.getenv("REDIS_URL"))  # Redis cache

# remove module-level DB connect to avoid import-time errors
# ── lazy models ───────────────────────────────────────────
_face_app = None
_body_model = None

def get_face_app():
    global _face_app
    if _face_app is None:
        import insightface
        _face_app = insightface.app.FaceAnalysis(name=os.getenv("FACE_MODEL"))
        _face_app.prepare(ctx_id=0, det_size=(640, 640))
    return _face_app

def get_body_model():
    global _body_model
    if _body_model is None:
        import torch
        _body_model = torchreid.models.build_model(
            name=os.getenv("BODY_MODEL"), num_classes=1
        ).eval()
        if torch.cuda.is_available():
            _body_model.cuda()
    return _body_model

@celery_app.task(name="preprocess")
def embed_image(uid: int, face_path: str, body_path: str):
    # ----- connect to Postgres when task runs
    pg = psycopg2.connect(os.getenv("DATABASE_URL"))

    # ----- face embedding
    face_img = cv2.imread(face_path)
    if face_img is None:
        raise ValueError(f"Cannot read {face_path}")
    faces = get_face_app().get(face_img)
    if not faces:
        raise ValueError("No face detected in selfie")
    face_emb = faces[0].normed_embedding.astype(np.float32)

    # ----- body embedding
    body_img = cv2.imread(body_path)
    if body_img is None:
        raise ValueError(f"Cannot read {body_path}")
    # convert BGR to RGB and to PIL
    body_img = cv2.cvtColor(body_img, cv2.COLOR_BGR2RGB)
    body_pil = Image.fromarray(body_img)
    body_tensor = Compose([Resize((256,128)), ToTensor()])(body_pil).unsqueeze(0)
    body_emb = get_body_model()(body_tensor).squeeze().detach().cpu().numpy().astype(np.float32)

    # ----- cache in Redis
    r.hset(f"user:{uid}:emb", mapping={
        "face": face_emb.tobytes(),
        "body": body_emb.tobytes()
    })

    # ----- upsert in Postgres
    with pg:
        with pg.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_embeddings(uid, face_emb, body_emb)
                VALUES (%s, %s::vector, %s::vector)
                ON CONFLICT (uid) DO UPDATE
                  SET face_emb = EXCLUDED.face_emb,
                      body_emb  = EXCLUDED.body_emb;
                """,
                (uid, list(face_emb), list(body_emb)),
            )
    pg.close()
