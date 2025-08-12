# models.py (compatibility shim)
# This module re-exports ORM models from app.models to prevent schema divergence.
# Use app.models directly in new code.

from app.database import Base
from app.models import User, UserEmbedding, SurferFrame, UserProfile, SurfVideo

__all__ = [
    "Base",
    "User",
    "UserEmbedding",
    "SurferFrame",
    "UserProfile",
    "SurfVideo",
]
