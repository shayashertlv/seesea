# create_db.py

from app.database import Base, engine
from app import create_app
from app.models import UserEmbedding, SurferFrame

# Create the Flask app context so you can use config if needed
app = create_app()

with app.app_context():
    print("Creating tables in SQLite database...")
    Base.metadata.create_all(bind=engine)
    print("Done.")
