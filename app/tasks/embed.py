# app/tasks/embed.py
import os
import json
import cv2
import numpy as np
from dotenv import load_dotenv
from celery import shared_task

from app.database import SessionLocal
from app.models import UserEmbedding

# ---------------- InsightFace (same as before) ----------------
_face_app = None

def _get_face_app():
    global _face_app
    if _face_app is not None:
        return _face_app

    load_dotenv()
    pack = os.getenv("INSIGHTFACE_PACK", "buffalo_l")
    providers = [p.strip() for p in os.getenv("INSIGHTFACE_PROVIDERS", "CPUExecutionProvider").split(",") if p.strip()]
    det_size = int(os.getenv("INSIGHTFACE_DET_SIZE", "640"))

    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name=pack, providers=providers)
    app.prepare(ctx_id=0, det_size=(det_size, det_size))
    _face_app = app
    return _face_app

def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v if n == 0 else (v / n)

def _select_best_face(faces):
    if not faces:
        return None
    best, best_val = None, -1
    for f in faces:
        x1, y1, x2, y2 = f.bbox.astype(int)
        area = max(0, x2 - x1) * max(0, y2 - y1)
        val = float(f.det_score) * (area ** 0.5)
        if val > best_val:
            best_val, best = val, f
    return best

def _compute_face_embedding_from_path(img_path: str) -> tuple[np.ndarray | None, dict | None, np.ndarray | None]:
    """
    Robust face extraction from a reference photo. Tries multiple candidate transforms
    to handle different head proportions (small/distant heads, off-center, etc.).
    Options can be set via environment variables:
      - REF_TRY_UPSCALE: 1/0 (default 1)
      - REF_UPSCALE_SCALES: comma list (default "1.3,1.6,2.0")
      - REF_TRY_CROPS: 1/0 (default 1)
      - REF_CROP_FRACTIONS: comma list of central crop keep-fractions (default "1.0,0.85,0.7,0.55")
      - REF_TOP_CROP_FRACTIONS: comma list of top-centered vertical keep-fractions (default "0.6,0.5")
      - REF_TRY_FLIP: 1/0 (default 1)
      - REF_MAX_CANDIDATES: int cap to avoid explosion (default 24)
    Returns: (embedding, face_bbox_in_candidate, candidate_image_used)
    """
    img = cv2.imread(img_path)
    if img is None:
        print(f"[embed] Failed to read image: {img_path}")
        return None, None, None

    # Helpers
    def _parse_floats(s: str, default: list[float]) -> list[float]:
        try:
            vals = [float(x.strip()) for x in s.split(',') if x.strip()]
            return vals if vals else default
        except Exception:
            return default

    def _center_crop(im: np.ndarray, keep: float) -> np.ndarray | None:
        if im is None or im.size == 0:
            return None
        keep = max(0.2, min(1.0, float(keep)))
        h, w = im.shape[:2]
        nh, nw = int(h * keep), int(w * keep)
        y1 = max(0, (h - nh) // 2)
        x1 = max(0, (w - nw) // 2)
        y2, x2 = y1 + nh, x1 + nw
        if nh < 10 or nw < 10:
            return None
        return im[y1:y2, x1:x2]

    def _top_center_crop(im: np.ndarray, vert_keep: float, horiz_keep: float = 0.8) -> np.ndarray | None:
        if im is None or im.size == 0:
            return None
        vert_keep = max(0.3, min(1.0, float(vert_keep)))
        horiz_keep = max(0.4, min(1.0, float(horiz_keep)))
        h, w = im.shape[:2]
        nh, nw = int(h * vert_keep), int(w * horiz_keep)
        y1, y2 = 0, nh
        x1 = max(0, (w - nw) // 2)
        x2 = x1 + nw
        if nh < 10 or nw < 10:
            return None
        return im[y1:y2, x1:x2]

    def _resize_scale(im: np.ndarray, scale: float) -> np.ndarray | None:
        try:
            return cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        except Exception:
            return None

    def _flip(im: np.ndarray) -> np.ndarray | None:
        try:
            return cv2.flip(im, 1)
        except Exception:
            return None

    # Options
    try_up = os.getenv("REF_TRY_UPSCALE", "1") not in ("0", "false", "False")
    up_scales = _parse_floats(os.getenv("REF_UPSCALE_SCALES", "1.3,1.6,2.0"), [1.3, 1.6, 2.0])
    try_crops = os.getenv("REF_TRY_CROPS", "1") not in ("0", "false", "False")
    crop_fracs = _parse_floats(os.getenv("REF_CROP_FRACTIONS", "1.0,0.85,0.7,0.55"), [1.0, 0.85, 0.7, 0.55])
    top_fracs = _parse_floats(os.getenv("REF_TOP_CROP_FRACTIONS", "0.6,0.5"), [0.6, 0.5])
    try_flip = os.getenv("REF_TRY_FLIP", "1") not in ("0", "false", "False")
    max_cand = int(os.getenv("REF_MAX_CANDIDATES", "24"))

    # Build candidate list (label, image)
    candidates: list[tuple[str, np.ndarray]] = []

    # 1) Base
    candidates.append(("orig", img))

    # 2) Center crops for different proportions
    if try_crops:
        for cf in crop_fracs:
            if abs(cf - 1.0) < 1e-6:
                continue  # orig already added
            cc = _center_crop(img, cf)
            if cc is not None:
                candidates.append((f"center_{cf:.2f}", cc))
        # 3) Top-centered crops (head often near top)
        for tf in top_fracs:
            tc = _top_center_crop(img, tf, 0.8)
            if tc is not None:
                candidates.append((f"top_{tf:.2f}", tc))

    # 4) Upscales of originals and some crops (limit to keep count reasonable)
    if try_up:
        base_for_up = [c for c in candidates[:3]]  # orig + first few crops
        for lbl, im in base_for_up:
            for s in up_scales:
                up = _resize_scale(im, s)
                if up is not None:
                    candidates.append((f"{lbl}_up{s:.2f}", up))

    # 5) Flips for a few early variants
    if try_flip:
        base_for_flip = [candidates[0]]  # flip only original to control growth
        for lbl, im in base_for_flip:
            fl = _flip(im)
            if fl is not None:
                candidates.append((f"{lbl}_flip", fl))

    # Cap candidates
    if len(candidates) > max_cand:
        candidates = candidates[:max_cand]

    app = _get_face_app()

    for label, cand in candidates:
        if cand is None or cand.size == 0:
            continue
        faces = app.get(cand)
        face = _select_best_face(faces)
        if face is None:
            continue
        emb = getattr(face, "normed_embedding", None)
        if emb is None:
            emb = getattr(face, "embedding", None)
        if emb is None:
            continue
        emb = _l2_normalize(np.asarray(emb, dtype=np.float32))
        x1, y1, x2, y2 = face.bbox.astype(int)
        print(f"[embed] Face detected using candidate '{label}' for {img_path}")
        return emb, {"x1": x1, "y1": y1, "x2": x2, "y2": y2}, cand

    print(f"[embed] No face detected in {img_path} across {len(candidates)} candidates")
    return None, None, None

# ---------------- Outfit color embedding ----------------

def _safe_crop(img, x1, y1, x2, y2):
    h, w = img.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))
    if x2 - x1 < 10 or y2 - y1 < 10:
        return None
    return img[y1:y2, x1:x2]

def _torso_roi_from_face(img, face_bbox):
    """Heuristic torso ROI: below the face, a bit wider and taller."""
    if not face_bbox:
        return None
    x1, y1, x2, y2 = face_bbox["x1"], face_bbox["y1"], face_bbox["x2"], face_bbox["y2"]
    fw = x2 - x1
    fh = y2 - y1
    cx = (x1 + x2) / 2

    # expand width, extend downward
    tw = 2.2 * fw
    th = 2.5 * fh
    tx1 = cx - tw / 2
    tx2 = cx + tw / 2
    ty1 = y2 + 0.15 * fh
    ty2 = y2 + th
    roi = _safe_crop(img, tx1, ty1, tx2, ty2)
    if roi is None:
        return None

    # Focus on central-lower patch (reduce water/background)
    h, w = roi.shape[:2]
    cx1, cy1 = int(w * 0.2), int(h * 0.2)
    cx2, cy2 = int(w * 0.8), int(h * 0.95)
    small = roi[cy1:cy2, cx1:cx2]
    return small if small.size else roi

def _hsv_hist(roi_bgr, h_bins=12, s_bins=4, v_bins=3) -> np.ndarray:
    """Compact HSV histogram (normalized), robust-ish to light."""
    if roi_bgr is None or roi_bgr.size == 0:
        return None
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    # Optional light smoothing
    hsv = cv2.GaussianBlur(hsv, (3, 3), 0)

    # Mask out super-dark or super-bright low-info pixels
    v = hsv[:, :, 2]
    s = hsv[:, :, 1]
    mask = cv2.inRange(hsv, (0, 40, 30), (180, 255, 245))  # drop very low sat/very dark/very bright

    hist = cv2.calcHist([hsv], [0, 1, 2], mask,
                        [h_bins, s_bins, v_bins],
                        [0, 180, 0, 256, 0, 256])
    hist = hist.flatten().astype(np.float32)
    ssum = float(hist.sum()) + 1e-8
    hist /= ssum
    return hist  # L1-normalized

def _upsert_user_embedding(session, user_id: int, emb_vec: np.ndarray, emb_type: str):
    emb_json = json.dumps((emb_vec.astype(float)).tolist())
    existing = session.query(UserEmbedding).filter_by(user_id=user_id, embedding_type=emb_type).first()
    if existing:
        existing.embedding = emb_json
    else:
        session.add(UserEmbedding(user_id=user_id, embedding=emb_json, embedding_type=emb_type))

# ---------------- Public API ----------------

load_dotenv()

def generate_face_embedding(user_id: int, face_path: str, image_type: str = "front", also_color: bool = True) -> bool:
    """
    Generate and store user's face embedding.
    Optionally also extracts outfit color embedding from the same candidate image used
    for face detection (ensures bbox consistency even when using crops/upscales).
    """
    session = SessionLocal()
    try:
        emb, face_bbox, cand_img = _compute_face_embedding_from_path(face_path)
        if emb is None:
            return False
        emb_type = f"face_{'front' if image_type == 'front' else 'side'}"
        _upsert_user_embedding(session, user_id, emb, emb_type)

        if also_color:
            base_img = cand_img if cand_img is not None else cv2.imread(face_path)
            torso = _torso_roi_from_face(base_img, face_bbox) if base_img is not None else None
            color_emb = _hsv_hist(torso)
            if color_emb is not None:
                _upsert_user_embedding(session, user_id, color_emb, "outfit_color")

        session.commit()
        print(f"[embed] Stored {emb_type} (and outfit_color={also_color}) for user {user_id}")
        return True
    except Exception as e:
        session.rollback()
        print(f"[embed] Error generating embeddings: {e}")
        return False
    finally:
        session.close()

# Celery task wrapper: keep sync API intact while exposing a task name
@shared_task(name="generate_face_embedding")
def _task_generate_face_embedding(user_id: int, face_path: str, image_type: str = "front", also_color: bool = True) -> bool:
    return generate_face_embedding(user_id, face_path, image_type, also_color)

