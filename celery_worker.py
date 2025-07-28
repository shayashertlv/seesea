# celery_worker.py  – real face-embedding worker
from celery import Celery
import os, numpy as np, cv2
from insightface.app import FaceAnalysis

# ---------- Celery setup ----------
BROKER_URL = "redis://localhost:6379/0"
celery = Celery("seesea", broker=BROKER_URL)

# ---------- load detector+embedder once ----------
face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
face_app.prepare(ctx_id=0, det_size=(640, 640))   # 640 is plenty for selfies


@celery.task
def embed_image(image_path: str):
    """
    Detects the largest face in `image_path`, extracts the 512-D ArcFace
    embedding, and saves it as <image_path>.npy
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(image_path)

    faces = face_app.get(img)          # returns list of Face objects
    if not faces:
        return f"No face found in {image_path}"

    # pick the biggest face (highest area bbox)
    face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
    vec = face.normed_embedding        # 512-float NumPy array, already L2-normed

    out_path = image_path + ".npy"
    np.save(out_path, vec.astype(np.float32))
    return out_path
