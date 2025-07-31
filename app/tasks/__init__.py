# app/__init__.py

from flask import Flask
from app.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints here when ready
    from app.auth import auth_bp
    from app.upload import upload_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)

    return app
