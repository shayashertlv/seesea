# app/tasks/match.py
import os
import json
import cv2
import numpy as np
from celery import shared_task
from dotenv import load_dotenv

from app.models import SurferFrame, UserEmbedding
from app.database import SessionLocal
from app.tasks.embed import _get_face_app, _l2_normalize, _select_best_face, _hsv_hist, _torso_roi_from_face

# ------------- Config -------------
load_dotenv()

MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.55"))   # final combined threshold (lowered default)
FACE_WEIGHT = float(os.getenv("FACE_WEIGHT", "0.75"))
COLOR_WEIGHT = float(os.getenv("COLOR_WEIGHT", "0.25"))
SIDE_WEIGHT = float(os.getenv("SIDE_WEIGHT", "0.90"))           # side faces counted slightly less than front
COLOR_ONLY_THRESHOLD = float(os.getenv("COLOR_ONLY_THRESHOLD", "0.40"))
FACE_MIN_ACCEPT = float(os.getenv("FACE_MIN_ACCEPT", "0.35"))    # accept if face strong enough with margin
TOP2_GAP = float(os.getenv("TOP2_GAP", "0.06"))                  # best-vs-second margin for acceptance
COLOR_ONLY_GAP = float(os.getenv("COLOR_ONLY_GAP", "0.08"))      # margin for color-only acceptance
DET_SIZE = int(os.getenv("INSIGHTFACE_DET_SIZE", "640"))


# ------------- Helpers -------------

def _resolve_image_path(p: str) -> str:
    if not p:
        return p
    # Normalize separators
    p_norm = p.replace("/", os.sep).replace("\\", os.sep)
    # If already absolute and exists, return
    if os.path.isabs(p_norm) and os.path.exists(p_norm):
        return p_norm
    # If it already includes app/static prefix
    if p_norm.startswith(os.path.join("app", "static")):
        return p_norm
    # Try under app/static
    candidate = os.path.join("app", "static", p_norm)
    if os.path.exists(candidate):
        return candidate
    # Fallback to original (cv2 can still try)
    return p_norm



def _extract_roi_if_available(img: np.ndarray, frame: SurferFrame) -> np.ndarray:
    """
    If your SurferFrame stores a bbox, crop to that region to help face detector.
    We try a few common field names. If none, return original img.
    Additionally, expand the bbox by a margin to include context (helps small faces).
    """
    # Try explicit fields
    for fields in (("x1", "y1", "x2", "y2"), ("bx1", "by1", "bx2", "by2"), ("left", "top", "right", "bottom")):
        if all(hasattr(frame, f) for f in fields):
            x1, y1, x2, y2 = [int(getattr(frame, f)) for f in fields]
            break
    else:
        # Try JSON field
        bbox_json = getattr(frame, "bbox", None) or getattr(frame, "bbox_json", None)
        if bbox_json:
            try:
                b = bbox_json if isinstance(bbox_json, dict) else json.loads(bbox_json)
                x1, y1, x2, y2 = map(int, [b.get("x1", 0), b.get("y1", 0), b.get("x2", img.shape[1]), b.get("y2", img.shape[0])])
            except Exception:
                return img
        else:
            return img

    # Sanitize coords
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 10 or y2 - y1 < 10:
        return img

    # Expand by margin
    bw = x2 - x1
    bh = y2 - y1
    margin = 0.2  # 20% margin around bbox
    ex1 = int(max(0, x1 - margin * bw))
    ey1 = int(max(0, y1 - margin * bh))
    ex2 = int(min(w, x2 + margin * bw))
    ey2 = int(min(h, y2 + margin * bh))

    return img[ey1:ey2, ex1:ex2]

def _compute_frame_face_embedding(frame: SurferFrame) -> np.ndarray | None:
    img_path = _resolve_image_path(frame.frame_path)
    img = cv2.imread(img_path)
    if img is None:
        print(f"[match] Could not read image at {img_path}")
        return None

    roi = _extract_roi_if_available(img, frame)
    app = _get_face_app()

    # Try ROI; if nothing, fall back to full image
    for candidate in (roi, img) if roi is not img else (img,):
        faces = app.get(candidate)
        face = _select_best_face(faces)
        if face is not None:
            emb = getattr(face, "normed_embedding", None)
            if emb is None:
                emb = getattr(face, "embedding", None)
            if emb is None:
                continue
            return _l2_normalize(np.asarray(emb, dtype=np.float32))

    print(f"[match] No face detected for frame {frame.id}")
    return None




def _hist_intersection(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.minimum(a, b).sum())

def _compute_frame_face_embedding_and_color(frame: SurferFrame):
    img_path = _resolve_image_path(frame.frame_path)
    img = cv2.imread(img_path)
    if img is None:
        print(f"[match] Could not read image at {img_path}")
        return None, None

    roi = _extract_roi_if_available(img, frame)
    app = _get_face_app()

    tried = []  # list of (label, image) candidates
    # Base candidates
    if roi is not None:
        tried.append(("roi", roi))
    if roi is not img:
        tried.append(("full", img))

    # Upscale small candidates to help detector
    def _maybe_upscale(im: np.ndarray) -> np.ndarray | None:
        if im is None:
            return None
        h, w = im.shape[:2]
        if max(h, w) < 600:
            scale = 1.8 if max(h, w) < 400 else 1.4
            try:
                return cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            except Exception:
                return None
        return None

    ups_roi = _maybe_upscale(roi)
    if ups_roi is not None:
        tried.append(("roi_up", ups_roi))
    ups_img = _maybe_upscale(img)
    if ups_img is not None:
        tried.append(("full_up", ups_img))

    # Flipped versions
    def _flip(im: np.ndarray) -> np.ndarray | None:
        try:
            return cv2.flip(im, 1)
        except Exception:
            return None

    flip_roi = _flip(roi) if roi is not None else None
    if flip_roi is not None:
        tried.append(("roi_flip", flip_roi))
    if roi is not img:
        flip_img = _flip(img)
        if flip_img is not None:
            tried.append(("full_flip", flip_img))

    best_face_emb, best_color = None, None
    for label, candidate in tried:
        if candidate is None or candidate.size == 0:
            continue
        faces = app.get(candidate)
        face = _select_best_face(faces)
        if face is not None:
            emb = getattr(face, "normed_embedding", None)
            if emb is None:
                emb = getattr(face, "embedding", None)
            if emb is not None:
                best_face_emb = _l2_normalize(np.asarray(emb, dtype=np.float32))
            # Use shared torso ROI logic from embed.py
            fb = face.bbox.astype(int)
            bbox = {"x1": int(fb[0]), "y1": int(fb[1]), "x2": int(fb[2]), "y2": int(fb[3])}
            torso = _torso_roi_from_face(candidate, bbox)
            best_color = _hsv_hist(torso)
            break

    if best_face_emb is None and best_color is None:
        base = roi if roi is not None else img
        h, w = base.shape[:2]
        y1, y2 = int(h * 0.35), int(h * 0.95)
        x1, x2 = int(w * 0.20), int(w * 0.80)
        low = base[y1:y2, x1:x2]
        best_color = _hsv_hist(low)

    return best_face_emb, best_color

def _load_user_embeddings(session):
    """Return:
       faces: dict[user_id] -> {"front":[vecs], "side":[vecs]}
       colors: dict[user_id] -> [vecs]
    """
    faces, colors = {}, {}
    rows = session.query(UserEmbedding).all()
    for r in rows:
        try:
            vec = np.asarray(json.loads(r.embedding), dtype=np.float32)
            if r.embedding_type in ("face_front", "face_side"):
                vec = _l2_normalize(vec)
                slot = "front" if r.embedding_type == "face_front" else "side"
                faces.setdefault(r.user_id, {"front": [], "side": []})[slot].append(vec)
            elif r.embedding_type == "outfit_color":
                colors.setdefault(r.user_id, []).append(vec)
        except Exception as e:
            print(f"[match] Bad embedding row (user {r.user_id}): {e}")
    return faces, colors

def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))

def _score_face(frame_emb: np.ndarray, user_vecs: dict) -> float:
    best_front = max((_cos(frame_emb, v) for v in user_vecs.get("front", [])), default=0.0)
    best_side  = max((_cos(frame_emb, v) for v in user_vecs.get("side",  [])), default=0.0)
    both_bonus = 0.01 if (user_vecs.get("front") and user_vecs.get("side")) else 0.0
    return max(best_front, SIDE_WEIGHT * best_side) + both_bonus

def _score_color(frame_color: np.ndarray, user_colors: list[np.ndarray]) -> float:
    if frame_color is None or not user_colors:
        return 0.0
    return max((_hist_intersection(frame_color, uc) for uc in user_colors), default=0.0)

def match_surfer_to_users(frame_id: int) -> int:
    session = SessionLocal()
    try:
        frame = session.query(SurferFrame).filter_by(id=frame_id).first()
        if not frame:
            print(f"[match] Frame {frame_id} not found")
            return 0

        f_face, f_color = _compute_frame_face_embedding_and_color(frame)
        faces_map, colors_map = _load_user_embeddings(session)

        if not faces_map and not colors_map:
            print("[match] No user embeddings in DB")
            return 0

        # Score all users
        candidates = []  # (uid, total, face_score, color_score)
        all_uids = set(list(faces_map.keys()) + list(colors_map.keys()))
        for uid in all_uids:
            face_score  = _score_face(f_face, faces_map.get(uid, {})) if f_face is not None else 0.0
            color_score = _score_color(f_color, colors_map.get(uid, [])) if f_color is not None else 0.0
            total = FACE_WEIGHT * face_score + COLOR_WEIGHT * color_score
            candidates.append((uid, total, face_score, color_score))

        if not candidates:
            print("[match] No candidates after scoring")
            return 0

        # Sort to get top-2
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_uid, best_total, best_face, best_color = candidates[0]
        second_total = candidates[1][1] if len(candidates) > 1 else -1.0
        second_face = candidates[1][2] if len(candidates) > 1 else -1.0
        margin_total = best_total - second_total
        margin_face = best_face - second_face

        # Color-only path
        if f_face is None and f_color is not None:
            if best_total >= COLOR_ONLY_THRESHOLD and (len(candidates) == 1 or margin_total >= COLOR_ONLY_GAP):
                frame.user_id = int(best_uid)
                frame.score = float(best_total)
                session.commit()
                print(f"[match] Frame {frame_id} -> user {best_uid} (color-only={best_total:.3f}, margin={margin_total:.3f})")
                return best_uid
            print(f"[match] No color-only match over threshold/margin for frame {frame_id} (best={best_total:.3f}, margin={margin_total:.3f})")
            return 0

        # Combined acceptance
        if best_total >= MATCH_THRESHOLD and (len(candidates) == 1 or margin_total >= TOP2_GAP):
            frame.user_id = int(best_uid)
            frame.score = float(best_total)
            session.commit()
            print(f"[match] Frame {frame_id} -> user {best_uid} (combined={best_total:.3f}, margin={margin_total:.3f})")
            return best_uid

        # Face-strong fallback acceptance
        if f_face is not None and best_face >= FACE_MIN_ACCEPT and (len(candidates) == 1 or margin_total >= TOP2_GAP or margin_face >= TOP2_GAP):
            frame.user_id = int(best_uid)
            frame.score = float(best_total)
            session.commit()
            print(f"[match] Frame {frame_id} -> user {best_uid} (face-strong={best_face:.3f}, total={best_total:.3f}, margin_t={margin_total:.3f}, margin_f={margin_face:.3f})")
            return best_uid

        print(f"[match] No match accepted for frame {frame_id} (best_total={best_total:.3f}, best_face={best_face:.3f}, margin_t={margin_total:.3f}, margin_f={margin_face:.3f})")
        return 0

    except Exception as e:
        session.rollback()
        print(f"[match] Error matching frame {frame_id}: {e}")
        return 0
    finally:
        session.close()

@shared_task(name="match_all_frames")
def match_all_frames():
    """
    Match all frames with user_id=0. Returns count of matched.
    """
    session = SessionLocal()
    try:
        to_match = session.query(SurferFrame).filter_by(user_id=0).all()
        print(f"[match] Found {len(to_match)} unmatched frames")
        count = 0
        for f in to_match:
            if match_surfer_to_users(f.id) > 0:
                count += 1
        return count
    except Exception as e:
        print(f"[match] Batch error: {e}")
        return 0
    finally:
        session.close()