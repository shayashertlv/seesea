# app/tasks/preprocess.py
# Deprecated: legacy pipeline (body embeddings, Redis cache) is not used anymore.
# All embedding/matching now uses app/tasks/embed.py and app/tasks/match.py only.
# This module is kept to avoid import errors and is intentionally disabled.


def preprocess_deprecated(*args, **kwargs):
    """
    Deprecated. Do not use.
    Use instead:
      - app.tasks.embed.generate_face_embedding
      - app.tasks.match.match_all_frames
    """
    raise RuntimeError(
        "preprocess is deprecated. Use embed.generate_face_embedding and the match workflow instead."
    )

# Backwards-compat alias if something imports 'preprocess'
preprocess = preprocess_deprecated
