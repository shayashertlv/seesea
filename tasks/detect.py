# tasks/detect.py
from celery import Celery
from ultralytics import YOLO
import os

# Initialize Celery with the same broker as other tasks
app = Celery("detect", broker=os.getenv("BROKER_URL"))

# Load the YOLO model once at startup, using the path from env or default
model = YOLO(
    os.getenv("SURFER_MODEL", "weights/surf_polish640_best.pt")
)

@app.task(name="detect", queue="video")
def detect(frame_path: str):
    """
    Runs YOLO detection on the given frame and returns a list of bounding boxes [x1, y1, x2, y2].
    """
    # Read desired image size from env or default
    imgsz = int(os.getenv("IMG_SIZE", "960"))
    # Optional: read confidence threshold and IoU from env
    conf = float(os.getenv("CONF_THRESHOLD", "0.25"))
    iou = float(os.getenv("IOU_THRESHOLD", "0.45"))

    # Run inference
    results = model(frame_path, imgsz=imgsz, conf=conf, iou=iou)
    # Extract bounding boxes as plain lists
    boxes = results[0].boxes.xyxy.cpu().tolist()
    return boxes
