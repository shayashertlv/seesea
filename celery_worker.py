# celery_worker.py – Celery app entrypoint (only required task modules included)
from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------- Celery setup ----------
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6380/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6380/0")

# Configure Celery app with explicit task modules (only needed ones)
celery = Celery(
    "seesea",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        'app.tasks.detect',
        'app.tasks.embed',
        'app.tasks.match',
        'app.tasks.process_video'
    ]
)

# Consistent time handling to avoid drift warnings across nodes
celery.conf.update(
    timezone=os.environ.get("CELERY_TIMEZONE", "UTC"),
    enable_utc=True,
)

# Tasks are discovered via 'include' list above; no direct imports here to avoid circular imports.

# Helper to enqueue process_video without exposing extra Celery tasks

def enqueue_process_video(video_id: int):
    """Enqueue the built-in 'process_video' Celery task by name.
    Returns AsyncResult. Logs broker and task id for visibility.
    """
    try:
        broker = os.environ.get("CELERY_BROKER_URL", "")
        res = celery.send_task('process_video', args=[video_id])
        print(f"[enqueue] Sent process_video(video_id={video_id}) task_id={getattr(res, 'id', None)} broker={broker}")
        return res
    except Exception as e:
        print(f"[enqueue] Failed to enqueue process_video(video_id={video_id}): {e}")
        raise