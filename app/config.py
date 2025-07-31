# app/config.py

import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev_secret")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "seesea.sqlite")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
