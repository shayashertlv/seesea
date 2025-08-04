import os
import cv2
from ultralytics import YOLO
from datetime import datetime
from app.database import SessionLocal
from app.models import SurferFrame
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

VIDEO_PATH = os.getenv("VIDEO_PATH", "app/static/uploads/sample_surf.mp4")
WEIGHTS_PATH = os.getenv("YOLO_WEIGHTS_PATH", "weights/surf_polish640_best.pt")
SAVE_DIR = os.getenv("CAPTURES_FOLDER", os.path.join("app", "static", "captures"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.3"))

def detect_and_capture():
    print("[✅] Starting detection...")

    if not os.path.exists(VIDEO_PATH):
        print(f"[❌] Video not found at {VIDEO_PATH}")
        return

    os.makedirs(SAVE_DIR, exist_ok=True)
    print("[✅] Directories checked/created.")

    print("[✅] Loading YOLO model...")
    model = YOLO(WEIGHTS_PATH)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("❌ Could not open video.")
        return

    session = SessionLocal()
    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[🛑] End of video.")
            break

        frame_count += 1
        print(f"[🔁] Processing frame {frame_count}...")

        results = model(frame)[0]
        for i, box in enumerate(results.boxes):
            conf = float(box.conf)
            if conf < CONFIDENCE_THRESHOLD:
                continue

            x1, y1, x2, y2 = map(float, box.xyxy[0])
            label = results.names[int(box.cls[0])]

            filename = f"frame_{frame_count}_{i}.jpg"
            # Create full path for file operations
            raw_path_full = os.path.join(SAVE_DIR, filename)              # Save with OS native path
            
            # Create relative path for database storage (without app/static/ prefix)
            captures_dir_relative = "captures"  # Relative path for database
            raw_path_relative = os.path.join(captures_dir_relative, filename)
            frame_path = raw_path_relative.replace("\\", "/")        # Store for web/flask

            crop = frame[int(y1):int(y2), int(x1):int(x2)]
            cv2.imwrite(raw_path_full, crop)

            # Store the frame without assigning to a user yet
            # The matching process will later assign the correct user_id
            new_frame = SurferFrame(
                user_id=0,  # Temporary placeholder, will be updated by matching process
                frame_path=frame_path,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                score=conf,
            )
            session.add(new_frame)
            saved_count += 1
            print(f"[💾] Saved: {filename} | Conf: {conf:.2f} | Label: {label}")

        if frame_count >= 100:
            print("[⏹️] Limit reached. Stopping after 100 frames.")
            break

    session.commit()
    cap.release()
    print(f"[✅] Done. Processed {frame_count} frames. Saved {saved_count} images.")

if __name__ == "__main__":
    detect_and_capture()
