# app/upload/__init__.py

from flask import Blueprint

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")

from app.upload import routes
