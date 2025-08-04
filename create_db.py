# create_db.py

from app.database import Base, engine
from app import create_app
from app.models import User, UserEmbedding, SurferFrame, UserProfile, SurfVideo
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create the Flask app context so you can use config if needed
app = create_app()

with app.app_context():
    db_url = os.environ.get("DATABASE_URL", "")
    db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"
    print(f"Creating tables in {db_type} database...")
    Base.metadata.create_all(bind=engine)
    print(f"Database tables created successfully in {db_type}.")