# create_db.py

from app.database import Base, engine
from app import create_app
from app.models import User, UserEmbedding, SurferFrame, UserProfile, SurfVideo
from dotenv import load_dotenv
from sqlalchemy import inspect, text
import os

# Load environment variables
load_dotenv()

# Create the Flask app context so you can use config if needed
app = create_app()

with app.app_context():
    db_url = os.environ.get("DATABASE_URL", "")
    db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"
    print(f"Creating tables in {db_type} database...")
    # Ensure all tables exist (new deployments will get the latest schema)
    Base.metadata.create_all(bind=engine)

    # Lightweight migrations for surfer_frames
    try:
        insp = inspect(engine)
        cols = [c['name'] for c in insp.get_columns('surfer_frames')]
        # Add video_id if missing
        if 'video_id' not in cols:
            print("Adding column surfer_frames.video_id (Integer, nullable=True)...")
            ddl = text("ALTER TABLE surfer_frames ADD COLUMN video_id INTEGER")
            with engine.begin() as conn:
                conn.execute(ddl)
            print("Column surfer_frames.video_id added successfully.")
        else:
            print("Column surfer_frames.video_id already present; no migration needed.")

        # Add created_at if missing
        if 'created_at' not in cols:
            print("Adding column surfer_frames.created_at (TIMESTAMP)...")
            if "postgresql" in db_url:
                ddl = text("ALTER TABLE surfer_frames ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()")
                with engine.begin() as conn:
                    conn.execute(ddl)
                    conn.execute(text("UPDATE surfer_frames SET created_at = NOW() WHERE created_at IS NULL"))
            else:
                ddl = text("ALTER TABLE surfer_frames ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                with engine.begin() as conn:
                    conn.execute(ddl)
            print("Column surfer_frames.created_at added or ensured.")
        else:
            print("Column surfer_frames.created_at already present; no migration needed.")

        # Add updated_at if missing
        if 'updated_at' not in cols:
            print("Adding column surfer_frames.updated_at (TIMESTAMP)...")
            if "postgresql" in db_url:
                ddl = text("ALTER TABLE surfer_frames ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()")
                with engine.begin() as conn:
                    conn.execute(ddl)
                    conn.execute(text("UPDATE surfer_frames SET updated_at = NOW() WHERE updated_at IS NULL"))
            else:
                ddl = text("ALTER TABLE surfer_frames ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                with engine.begin() as conn:
                    conn.execute(ddl)
            print("Column surfer_frames.updated_at added or ensured.")
        else:
            print("Column surfer_frames.updated_at already present; no migration needed.")
    except Exception as e:
        print(f"Warning: Could not verify/apply migrations for surfer_frames: {e}")

    print(f"Database ready ({db_type}).")