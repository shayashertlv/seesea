# celery_worker.py  – real face-embedding worker
from celery import Celery
import os, numpy as np, cv2
from insightface.app import FaceAnalysis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------- Celery setup ----------
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6380/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6380/0")

# Configure Celery app with explicit task modules
celery = Celery(
    "seesea",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        'celery_worker',
        'app.tasks.match',
        'app.tasks.process_video'
    ]
)

# Import tasks from other modules
from app.tasks.match import match_all_frames
from app.tasks.process_video import process_video

# No need to register these tasks again as they are already registered in their respective modules
# We just need to include them in the Celery app's imports

# Keep process_video_task for backward compatibility
@celery.task(name="process_video_task")
def process_video_task(video_id):
    """
    Celery task to process a video by detecting surfers and matching them to users.
    This is a wrapper around the process_video task for backward compatibility.
    
    Args:
        video_id: ID of the SurfVideo to process
        
    Returns:
        True if processing was successful, False otherwise
    """
    # Use apply_async with explicit task name to ensure it's routed correctly
    return celery.send_task('process_video', args=[video_id])

# ---------- load detector+embedder once ----------
face_app = FaceAnalysis(name=os.environ.get("FACE_MODEL_NAME", "buffalo_l"), providers=["CPUExecutionProvider"])
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