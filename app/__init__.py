# app/__init__.py

from flask import Flask, render_template
from app.config import Config
from flask_login import LoginManager
from app.models import User, SurferFrame, UserProfile, SurfVideo
from app.database import SessionLocal
import os
import click

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

    # Landing page
    @app.route("/")
    def landing():
        return render_template("landing.html")

    # Maintenance CLI: clean-missing
    @app.cli.command("clean-missing")
    @click.option("--dry-run", is_flag=True, help="Scan and report without modifying the database.")
    def clean_missing(dry_run):
        """
        Delete SurferFrame rows whose files are missing on disk; clean or delete broken UserProfile/SurfVideo refs.
        """
        base_static = os.path.join("app", "static")
        session = SessionLocal()

        def _norm(p):
            p = (p or "").replace("\\", "/").lstrip("/")
            if p.startswith("app/static/"):
                p = p[len("app/static/"):]
            elif p.startswith("static/"):
                p = p[len("static/"):]
            return p

        removed_frames = 0
        removed_profiles = 0
        cleared_profile_side = 0
        removed_videos = 0
        cleared_thumbnails = 0

        try:
            # SurferFrame cleanup
            for f in session.query(SurferFrame).all():
                rel = _norm(f.frame_path)
                disk = os.path.join(base_static, rel)
                if not os.path.exists(disk):
                    session.delete(f)
                    removed_frames += 1

            # UserProfile cleanup
            for p in session.query(UserProfile).all():
                face_rel = _norm(p.face_image_path)
                face_disk = os.path.join(base_static, face_rel) if face_rel else ""
                side_rel = _norm(p.face_side_image_path) if getattr(p, "face_side_image_path", None) else ""
                side_disk = os.path.join(base_static, side_rel) if side_rel else ""

                missing_face = not face_rel or not os.path.exists(face_disk)
                missing_side = side_rel and not os.path.exists(side_disk)

                if missing_face:
                    session.delete(p)
                    removed_profiles += 1
                else:
                    if missing_side and getattr(p, "face_side_image_path", None):
                        p.face_side_image_path = None
                        cleared_profile_side += 1

            # SurfVideo cleanup
            for v in session.query(SurfVideo).all():
                video_rel = _norm(v.video_path)
                video_disk = os.path.join(base_static, video_rel) if video_rel else ""
                thumb_rel = _norm(v.thumbnail_path) if getattr(v, "thumbnail_path", None) else ""
                thumb_disk = os.path.join(base_static, thumb_rel) if thumb_rel else ""

                if not video_rel or not os.path.exists(video_disk):
                    session.delete(v)
                    removed_videos += 1
                else:
                    if thumb_rel and not os.path.exists(thumb_disk):
                        v.thumbnail_path = None
                        cleared_thumbnails += 1

            if dry_run:
                session.rollback()
            else:
                session.commit()

            click.echo(f"Removed SurferFrame rows: {removed_frames}")
            click.echo(f"Removed UserProfile rows (missing face): {removed_profiles}")
            click.echo(f"Cleared UserProfile side images: {cleared_profile_side}")
            click.echo(f"Removed SurfVideo rows (missing video): {removed_videos}")
            click.echo(f"Cleared SurfVideo thumbnails: {cleared_thumbnails}")
            if dry_run:
                click.echo("Dry-run: no changes persisted.")
        except Exception as e:
            session.rollback()
            click.echo(f"Error during cleanup: {e}")
        finally:
            session.close()

    # Maintenance CLI: delete-frame
    @app.cli.command("delete-frame")
    @click.option("--id", "frame_id", required=True, type=int, help="SurferFrame id to delete with its file.")
    def delete_frame(frame_id):
        """
        Delete a specific SurferFrame row and remove its file from disk.
        """
        base_static = os.path.join("app", "static")
        session = SessionLocal()

        def _norm(p):
            p = (p or "").replace("\\", "/").lstrip("/")
            if p.startswith("app/static/"):
                p = p[len("app/static/"):]
            elif p.startswith("static/"):
                p = p[len("static/"):]
            return p

        try:
            f = session.query(SurferFrame).get(frame_id)
            if not f:
                click.echo(f"No SurferFrame with id={frame_id}")
                return
            rel = _norm(f.frame_path)
            disk = os.path.join(base_static, rel)
            # Delete file if exists
            try:
                if rel and os.path.exists(disk):
                    os.remove(disk)
                    click.echo(f"Deleted file: {disk}")
            except Exception as fe:
                click.echo(f"Warning: could not delete file {disk}: {fe}")
            session.delete(f)
            session.commit()
            click.echo(f"Deleted SurferFrame id={frame_id}")
        except Exception as e:
            session.rollback()
            click.echo(f"Error deleting frame: {e}")
        finally:
            session.close()

    return app
