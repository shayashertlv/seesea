# web/upload/routes.py  – handles selfie + body photo upload
# ------------------------------------------------------
from pathlib import Path
from flask import Blueprint, request, current_app, jsonify
import os

from tasks.preprocess import embed_image  # Celery task: uid, face_path, body_path

# Removed login requirement for testing
upload_bp = Blueprint("upload", __name__, url_prefix="/upload")

@upload_bp.route("/selfie", methods=["POST"])
def selfie():
    """
    Expects multipart-form with keys:
      • face_img  – close selfie (JPEG/PNG)
      • body_img  – torso / wetsuit shot
    Saves both files, then queues Celery task to build embeddings.
    """
    try:
        face_file = request.files["face_img"]
        body_file = request.files["body_img"]
    except KeyError:
        return jsonify({"error": "face_img and body_img are required"}), 400

    # Determine user ID: use environment override or default to 1 for testing
    user_id = int(os.getenv("TEST_USER_ID", "1"))

    # user-specific folder
    user_dir = (
        Path(current_app.config.get("UPLOAD_FOLDER", "uploads")) / str(user_id)
    )
    user_dir.mkdir(parents=True, exist_ok=True)

    face_path = user_dir / "face.jpg"
    body_path = user_dir / "body.jpg"

    face_file.save(face_path)
    body_file.save(body_path)

    # async embedding
    embed_image.delay(user_id, face_path.as_posix(), body_path.as_posix())

    return jsonify({"status": "queued"}), 202
