# SeeSea - AI-Powered Surfer Photography

SeeSea is an AI-powered surfer photography service that uses high-resolution cameras and computer vision to automatically capture and deliver high-quality surfing images. The system identifies registered surfers in real time, tracks them, and adjusts camera framing dynamically to ensure optimal shots.

## Setup Instructions

### Prerequisites

- Python 3.10.9
- PostgreSQL (running on port 5433)
- Redis (running on port 6380)
- Docker (for running PostgreSQL and Redis containers)

### Docker Setup

The project uses Docker containers for PostgreSQL and Redis. Make sure Docker is running and execute:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5433
- Redis on port 6380

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

If you encounter issues with protobuf and onnx dependencies, you can try:

```bash
pip install protobuf==3.20.0 --force-reinstall
```

### Database Connection Issues

Make sure PostgreSQL is running and accessible:

```bash
psql -h localhost -p 5433 -U seesea -d seesea
```

The default password is `seesea`.