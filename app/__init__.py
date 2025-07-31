# app/__init__.py

from flask import Flask
from app.config import Config
from flask_login import LoginManager
from app.models import User
from app.database import SessionLocal

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        session = SessionLocal()
        return session.query(User).get(int(user_id))

    # Register blueprints
    from app.auth import auth_bp
    from app.upload import upload_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)

    return app
