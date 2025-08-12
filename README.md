# SeeSea - AI-Powered Surfer Photography

SeeSea is an AI-powered surfer photography service that uses high-resolution cameras and computer vision to automatically capture and deliver high-quality surfing images. The system identifies registered surfers in real time, tracks them, and adjusts camera framing dynamically to ensure optimal shots.

## Setup Instructions

### Prerequisites

- Python 3.10.9
- PostgreSQL (running on port 5433)
- Redis (running on port 6380)
- Docker (for running PostgreSQL and Redis containers)

### Docker Setup

The project uses Docker containers for PostgreSQL, Redis, and the Celery worker. Make sure Docker is running and execute:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5433
- Redis on port 6380
- Celery worker (connected to Redis and Postgres via the Docker network)

Notes:
- On Windows, Celery cannot run natively; running the worker via Docker is the recommended approach.
- To view worker logs: `docker-compose logs -f celery-worker`

### Environment Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

> **Note about protobuf**: The project uses protobuf 3.20.0, which conflicts with onnx 1.18.0 (which requires protobuf>=4.25.1). This is a known issue but doesn't affect the core functionality of the application.

### Database Setup

Initialize the PostgreSQL database:

```bash
python create_db.py
```

### Running the Application

1. Start the Flask development server:

```bash
flask run
```

2. Start the Celery worker (in a separate terminal):

```bash
celery -A celery_worker worker --loglevel=info
```

## Project Structure

- `app/` - Main application code
  - `auth/` - Authentication routes and forms
  - `tasks/` - Background tasks (detection, embedding, matching)
  - `upload/` - File upload routes and forms
  - `templates/` - HTML templates
  - `static/` - Static files (CSS, JS, uploads, captures)
- `weights/` - YOLO model weights
- `instance/` - Instance-specific files

## Configuration

The application is configured using environment variables in the `.env` file:

- Database: PostgreSQL on port 5433
- Redis: Running on port 6380
- YOLO model: Located in weights/surf_polish640_best.pt
- Confidence threshold: 0.3
- Match threshold: 0.8

## Database Migration

The project has been migrated from SQLite to PostgreSQL for better performance and scalability. If you have existing data in SQLite that you want to migrate:

1. Export data from SQLite:
   ```bash
   sqlite3 instance/seesea.sqlite .dump > seesea_dump.sql
   ```

2. Modify the SQL dump to be compatible with PostgreSQL syntax

3. Import into PostgreSQL:
   ```bash
   psql -h localhost -p 5433 -U seesea -d seesea -f seesea_dump.sql
   ```

## Troubleshooting

### Dependency Issues

- Protobuf/ONNX: If you encounter issues with protobuf and onnx dependencies, you can try:

```bash
pip install protobuf==3.20.0 --force-reinstall
```

- OpenCV/Numpy: We pin opencv-python==4.10.0.84 to remain compatible with numpy==1.26.4. Newer OpenCV (>=4.12) requires numpy>=2 which conflicts with parts of this stack. If you upgrade numpy to 2.x, audit dependent packages (e.g., scikit-learn, scipy, pandas, torchvision) for compatibility.

- Celery worker builds in Docker: The celery-worker container installs build tools and prefers wheels to satisfy packages like insightface and scientific deps. Ensure your docker-compose.yml includes:
  - apt packages: build-essential, python3-dev, cmake, libopenblas-dev, ffmpeg, libgl1, libglib2.0-0
  - environment: PIP_PREFER_BINARY=1
  - and that the command upgrades pip/setuptools/wheel before installing requirements.
  Rebuild with: `docker-compose up -d --build celery-worker`.

### Database Connection Issues

Make sure PostgreSQL is running and accessible:

```bash
psql -h localhost -p 5433 -U seesea -d seesea
```

The default password is `seesea`.

## Celery Notes

### Tasks visibility in worker logs
If the Celery worker does not list a function under the [tasks] section, it means that function is not registered as a Celery task. Only callables decorated with @shared_task (or @celery.task) are registered and listed.

In this project, we expose selected functions as tasks via thin wrappers so they can still be used synchronously in the web app:
- detect_and_capture (app/tasks/detect.py)
- generate_face_embedding (app/tasks/embed.py)
- match_all_frames (app/tasks/match.py)
- process_video (app/tasks/process_video.py)

### Clock drift warnings during mingle
If you see a warning like:

  WARNING/MainProcess Substantial drift from celery@HOST may mean clocks are out of sync

it’s typically due to timezone differences (e.g., container UTC vs host local time) observed during Celery’s gossip/mingle phase. In docker-compose we:
- Set TZ=UTC and CELERY_TIMEZONE=UTC
- Start the worker with --without-mingle --without-gossip when running a single worker

This prevents spurious drift warnings while keeping consistent timestamps.


## Face Recognition: Robust Reference Photo Handling

When a user uploads a face/reference photo that is not tightly cropped (e.g., the head is small or off-center), the system now tries multiple transforms to find the face reliably. This improves recognition downstream.

Behavior is configurable via environment variables (set in your .env or docker-compose):

- REF_TRY_UPSCALE: 1/0 (default 1). Try upscaling candidates to help detect small heads.
- REF_UPSCALE_SCALES: Comma-separated scales (default "1.3,1.6,2.0"). Applied to a few base crops.
- REF_TRY_CROPS: 1/0 (default 1). Try center and top-centered crops to simulate different head proportions.
- REF_CROP_FRACTIONS: Center-crop keep-fractions (default "1.0,0.85,0.7,0.55"). 1.0 means original.
- REF_TOP_CROP_FRACTIONS: Top-centered vertical keep-fractions (default "0.6,0.5").
- REF_TRY_FLIP: 1/0 (default 1). Try a horizontal flip of the original as a candidate.
- REF_MAX_CANDIDATES: Max number of candidates to try (default 24).

Notes:
- The outfit color embedding is computed from the same candidate image used for face detection, ensuring the face bbox aligns with the torso crop even when using crops/upscales.
- You can tune these knobs for speed vs. robustness. For faster processing, disable flips and reduce the number of scales/crops.

Example .env snippet:

```
REF_TRY_UPSCALE=1
REF_UPSCALE_SCALES=1.3,1.6
REF_TRY_CROPS=1
REF_CROP_FRACTIONS=1.0,0.85,0.7
REF_TOP_CROP_FRACTIONS=0.6
REF_TRY_FLIP=0
REF_MAX_CANDIDATES=16
```
