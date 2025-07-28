# web/__init__.py
import os
from dotenv import load_dotenv
load_dotenv()   # load .env into environment variables

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_mgr = LoginManager()

def create_app():
    app = Flask(__name__, instance_relative_config=False)

    # ── Testing overrides (disable auth & CSRF for pipeline testing) ───
    app.config['LOGIN_DISABLED'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # ── App configuration ─────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'please-change-this')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ── Initialize extensions ─────────────────────────────────────────
    db.init_app(app)
    login_mgr.init_app(app)
    login_mgr.login_view = 'auth.login'

    # ── Register blueprints ───────────────────────────────────────────
    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from .upload.routes import upload_bp
    app.register_blueprint(upload_bp)

    return app
