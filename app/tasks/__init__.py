"""Tasks package

This package contains Celery task modules and helper functions used by the
background processing pipeline (detection, embedding, matching, and video processing).

Modules are discovered by celery_worker.py via its include= list. There is no Flask app
definition here by design.
"""
