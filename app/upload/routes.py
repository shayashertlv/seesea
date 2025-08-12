# app/upload/routes.py

import os
import cv2
import numpy as np
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.upload import upload_bp
from app.upload.forms import UploadForm
from app.upload.video_forms import VideoUploadForm
from app.tasks.embed import generate_face_embedding
from celery_worker import enqueue_process_video
from app.database import SessionLocal
from app.models import UserProfile, SurferFrame, SurfVideo, UserEmbedding
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get upload folder from environment or use default
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "app/static/uploads")

def validate_face_image(image_path):
    """Validate face presence using the same pipeline as embed.py.
    Returns True if a valid face embedding can be computed, False otherwise.
    """
    try:
        from app.tasks.embed import _compute_face_embedding_from_path
        result = _compute_face_embedding_from_path(image_path)
        emb = result[0] if isinstance(result, (tuple, list)) else result
        return emb is not None
    except Exception as e:
        print(f"[routes.upload] Error validating face image with embed pipeline: {str(e)}")
        return False

@upload_bp.route("/", methods=["GET", "POST"])
@login_required
def upload_page():
    form = UploadForm()
    if form.validate_on_submit():
        # Get form data
        face_file = form.face_image.data
        face_side_file = form.face_image_side.data if form.face_image_side.data else None
        wetsuit_description = form.wetsuit_description.data
        
        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Generate unique filenames with timestamp to avoid overwriting
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        face_filename = secure_filename(f"{current_user.username}_face_{timestamp}.jpg")
        face_side_filename = None
        
        # Save the files (full paths for file operations)
        face_path = os.path.join(UPLOAD_FOLDER, face_filename)
        face_side_path = None
        
        # Create relative paths for database storage (without app/static/ prefix)
        uploads_dir_relative = "uploads"
        face_path_relative = os.path.join(uploads_dir_relative, face_filename)
        face_side_path_relative = None
        
        face_file.save(face_path)
        
        # Validate face image
        if not validate_face_image(face_path):
            # Remove the invalid image
            os.remove(face_path)
            flash("No face detected in the uploaded image. Please upload a clear face photo.", "error")
            return render_template("upload.html", form=form)
        
        # Save side face image if provided
        if face_side_file:
            face_side_filename = secure_filename(f"{current_user.username}_face_side_{timestamp}.jpg")
            face_side_path = os.path.join(UPLOAD_FOLDER, face_side_filename)
            face_side_path_relative = os.path.join(uploads_dir_relative, face_side_filename)
            face_side_file.save(face_side_path)
            
            # Validate side face image
            if not validate_face_image(face_side_path):
                # Remove the invalid image but continue with the process
                os.remove(face_side_path)
                face_side_path = None
                face_side_path_relative = None
                face_side_filename = None
                flash("No face detected in the side view image. It will be ignored.", "warning")
        
        # Generate embeddings with error handling
        ok_front = generate_face_embedding(current_user.id, face_path, "front")
        if not ok_front:
            # Clean up files and abort
            try:
                if os.path.exists(face_path):
                    os.remove(face_path)
                if face_side_path and os.path.exists(face_side_path):
                    os.remove(face_side_path)
            except Exception:
                pass
            flash("Could not extract a valid face embedding from your front image. Please upload a clearer face photo.", "error")
            return render_template("upload.html", form=form)

        ok_side = True
        if face_side_path:
            ok_side = generate_face_embedding(current_user.id, face_side_path, "side")
            if not ok_side:
                try:
                    if os.path.exists(face_side_path):
                        os.remove(face_side_path)
                except Exception:
                    pass
                face_side_path = None
                face_side_path_relative = None
                flash("We couldn't extract a valid face from the side image. It will be ignored.", "warning")
        
        # Store in UserProfile
        session = SessionLocal()
        try:
            # Check if user already has a profile
            existing_profile = session.query(UserProfile).filter_by(user_id=current_user.id).first()
            
            if existing_profile:
                # Update existing profile with relative paths
                existing_profile.face_image_path = face_path_relative
                existing_profile.face_side_image_path = face_side_path_relative
                existing_profile.wetsuit_description = wetsuit_description
            else:
                # Create new profile with relative paths
                new_profile = UserProfile(
                    user_id=current_user.id,
                    face_image_path=face_path_relative,
                    face_side_image_path=face_side_path_relative,
                    wetsuit_description=wetsuit_description
                )
                session.add(new_profile)
                
            # Warn if outfit color embedding wasn't extracted
            try:
                has_color = session.query(UserEmbedding).filter_by(user_id=current_user.id, embedding_type="outfit_color").first() is not None
                if not has_color:
                    flash("We couldn't reliably extract your outfit/wetsuit color from the photo. Matching will rely more on face features.", "warning")
            except Exception:
                # Non-fatal
                pass

            session.commit()
            flash("Reference images uploaded and embeddings generated successfully!", "success")
            
        except Exception as e:
            flash(f"Error saving profile: {str(e)}", "error")
            
        finally:
            session.close()
            
        return redirect(url_for("upload.upload_page"))

    return render_template("upload.html", form=form)

@upload_bp.route("/profile")
@login_required
def profile():
    """
    Display the user's profile page with reference images and surf photos.
    """
    session = SessionLocal()
    
    try:
        # Get user profile
        profile = session.query(UserProfile).filter_by(user_id=current_user.id).first()
        
        # Get user's surf photos (newest first)
        if hasattr(SurferFrame, 'created_at'):
            frames = session.query(SurferFrame).filter_by(user_id=current_user.id).order_by(SurferFrame.created_at.desc()).all()
        else:
            frames = session.query(SurferFrame).filter_by(user_id=current_user.id).order_by(SurferFrame.id.desc()).all()
        
        # Normalize and filter out frames that no longer exist on disk
        base_static = os.path.join("app", "static")
        clean_frames = []
        for f in frames:
            p = (f.frame_path or "").replace("\\", "/")
            if p.startswith("app/static/"):
                p = p[len("app/static/"):]
            elif p.startswith("static/"):
                p = p[len("static/"):]
            disk_path = os.path.join(base_static, p)
            if os.path.exists(disk_path):
                f.frame_path = p
                clean_frames.append(f)
        frames = clean_frames
        
        return render_template("profile.html", profile=profile, frames=frames)
        
    except Exception as e:
        flash(f"Error loading profile: {str(e)}", "error")
        return redirect(url_for("upload.upload_page"))
        
    finally:
        session.close()

@upload_bp.route("/gallery")
@login_required
def gallery():
    """
    Display the user's gallery of surf photos with filtering, sorting, and pagination.
    """
    # Get filter, sort, and pagination parameters from request
    sort_option = request.args.get('sort', 'date_desc')
    min_score = float(request.args.get('min_score', 0))
    view_option = request.args.get('view', 'grid')
    date_range = request.args.get('date_range', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)  # Number of photos per page
    
    session = SessionLocal()
    
    try:
        # Base query - get frames for current user with minimum score
        query = session.query(SurferFrame).filter_by(user_id=current_user.id).filter(SurferFrame.score >= min_score)
        
        # Apply date range filter if SurferFrame has created_at field
        if hasattr(SurferFrame, 'created_at'):
            from datetime import datetime, timedelta
            now = datetime.now()

            if date_range == 'today':
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(SurferFrame.created_at >= start)
            elif date_range == 'week':
                start = now - timedelta(days=7)
                query = query.filter(SurferFrame.created_at >= start)
            elif date_range == 'month':
                start = now - timedelta(days=30)
                query = query.filter(SurferFrame.created_at >= start)
        
        # Apply sorting
        if sort_option == 'date_asc':
            if hasattr(SurferFrame, 'created_at'):
                query = query.order_by(SurferFrame.created_at.asc())
            else:
                query = query.order_by(SurferFrame.id.asc())
        elif sort_option == 'date_desc':
            if hasattr(SurferFrame, 'created_at'):
                query = query.order_by(SurferFrame.created_at.desc())
            else:
                query = query.order_by(SurferFrame.id.desc())
        elif sort_option == 'score_asc':
            query = query.order_by(SurferFrame.score.asc())
        elif sort_option == 'score_desc':
            query = query.order_by(SurferFrame.score.desc())
        
        # Get total count for pagination
        total_count = query.count()
        
        # Calculate pagination values
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        offset = (page - 1) * per_page
        
        # Get frames for current page
        frames = query.limit(per_page).offset(offset).all()
        
        # Process frame paths and filter out missing files to avoid 404s
        base_static = os.path.join("app", "static")
        clean_frames = []
        for frame in frames:
            p = (frame.frame_path or "").replace("\\", "/")
            if p.startswith("app/static/"):
                p = p[len("app/static/"):]
            elif p.startswith("static/"):
                p = p[len("static/"):]
            disk_path = os.path.join(base_static, p)
            if os.path.exists(disk_path):
                frame.frame_path = p
                clean_frames.append(frame)
        frames = clean_frames
        
        # Create pagination metadata
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if page < total_pages else None,
        }
        
        # Render template with frames, pagination, and filter/sort options
        return render_template(
            "gallery.html", 
            frames=frames,
            pagination=pagination,
            sort_option=sort_option,
            min_score=min_score,
            view_option=view_option,
            date_range=date_range
        )
        
    except Exception as e:
        flash(f"Error loading gallery: {str(e)}", "error")
        return redirect(url_for("upload.profile"))
        
    finally:
        session.close()

@upload_bp.route("/video", methods=["GET", "POST"])
@login_required
def video_upload():
    """
    Handle video upload and display the video upload form.
    """
    form = VideoUploadForm()
    
    if form.validate_on_submit():
        video_file = form.video_file.data
        location = form.location.data
        description = form.description.data
        
        # Create upload directory if it doesn't exist
        video_upload_folder = os.getenv("VIDEO_UPLOAD_FOLDER", "app/static/videos")
        os.makedirs(video_upload_folder, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        video_filename = secure_filename(f"{current_user.username}_video_{timestamp}.mp4")
        
        # Create full path for file operations
        video_path = os.path.join(video_upload_folder, video_filename)
        
        # Create relative path for database storage (without app/static/ prefix)
        videos_dir_relative = "videos"
        video_path_relative = os.path.join(videos_dir_relative, video_filename)
        
        # Save the video file
        video_file.save(video_path)
        
        # Get video metadata using OpenCV
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                flash("Error: Could not open video file.", "error")
                os.remove(video_path)  # Remove the invalid video
                return redirect(url_for("upload.video_upload"))
                
            # Get video properties
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            # Create thumbnail
            thumbnail_folder = os.path.join(video_upload_folder, "thumbnails")
            os.makedirs(thumbnail_folder, exist_ok=True)
            thumbnail_filename = f"{os.path.splitext(video_filename)[0]}_thumb.jpg"
            
            # Create full path for file operations
            thumbnail_path = os.path.join(thumbnail_folder, thumbnail_filename)
            
            # Create relative path for database storage (without app/static/ prefix)
            thumbnails_dir_relative = os.path.join(videos_dir_relative, "thumbnails")
            thumbnail_path_relative = os.path.join(thumbnails_dir_relative, thumbnail_filename)
            
            # Read the first frame for thumbnail
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(thumbnail_path, frame)
            else:
                thumbnail_path = None
                thumbnail_path_relative = None
                
            cap.release()
            
            # Store video information in database
            session = SessionLocal()
            try:
                new_video = SurfVideo(
                    user_id=current_user.id,
                    video_path=video_path_relative,
                    thumbnail_path=thumbnail_path_relative,
                    location=location,
                    description=description,
                    duration=duration,
                    frame_count=frame_count,
                    status="pending"
                )
                session.add(new_video)
                session.commit()
                
                # Get the video ID for redirect
                video_id = new_video.id
                
                # Normalize stored paths to forward slashes for consistency across OS/container
                if new_video.video_path:
                    new_video.video_path = str(new_video.video_path).replace("\\", "/")
                if new_video.thumbnail_path:
                    new_video.thumbnail_path = str(new_video.thumbnail_path).replace("\\", "/")
                try:
                    # Queue the video processing task in Celery
                    async_res = enqueue_process_video(video_id)
                    current_app.logger.info(
                        "[enqueue] Sent process_video(video_id=%s) task_id=%s to broker=%s",
                        video_id,
                        getattr(async_res, "id", None),
                        os.getenv("CELERY_BROKER_URL")
                    )
                    flash("Video uploaded successfully! Processing has started automatically.", "success")
                except Exception as e:
                    current_app.logger.exception("[enqueue] Failed to dispatch process_video(video_id=%s)", video_id)
                    flash(f"Video uploaded, but failed to start processing automatically. You can press 'Process' on the video page. Error: {e}", "error")
                return redirect(url_for("upload.video_status", video_id=video_id))
                
            except Exception as e:
                flash(f"Error saving video information: {str(e)}", "error")
                return redirect(url_for("upload.video_upload"))
                
            finally:
                session.close()
                
        except Exception as e:
            flash(f"Error processing video: {str(e)}", "error")
            # Clean up the file if there was an error
            if os.path.exists(video_path):
                os.remove(video_path)
            return redirect(url_for("upload.video_upload"))
    
    # Get user's videos for display
    session = SessionLocal()
    try:
        videos = session.query(SurfVideo).filter_by(user_id=current_user.id).order_by(SurfVideo.created_at.desc()).limit(5).all()
        return render_template("video_upload.html", form=form, videos=videos)
        
    except Exception as e:
        flash(f"Error loading videos: {str(e)}", "error")
        return render_template("video_upload.html", form=form, videos=[])
        
    finally:
        session.close()

@upload_bp.route("/video/<int:video_id>")
@login_required
def video_status(video_id):
    """
    Display the status of a video's processing.
    """
    session = SessionLocal()
    
    try:
        # Get the video
        video = session.query(SurfVideo).filter_by(id=video_id, user_id=current_user.id).first()
        
        if not video:
            flash("Video not found or you don't have permission to view it.", "error")
            return redirect(url_for("upload.video_upload"))
            
        # Process thumbnail path if it exists (normalize slashes and strip static prefix)
        if video.thumbnail_path:
            pthumb = str(video.thumbnail_path).replace("\\", "/")
            if pthumb.startswith("app/static/"):
                pthumb = pthumb[len("app/static/"):]
            elif pthumb.startswith("static/"):
                pthumb = pthumb[len("static/"):]
            video.thumbnail_path = pthumb
            
        # Get frames from this video that have been matched to the current user
        # Prefer filtering by video_id (requires DB column 'video_id'). Fallback to user-only if unavailable.
        try:
            frames = session.query(SurferFrame).filter_by(user_id=current_user.id, video_id=video_id).all()
        except Exception:
            frames = session.query(SurferFrame).filter_by(user_id=current_user.id).all()
        
        # Process frame paths to ensure they work correctly with url_for('static', ...)
        for frame in frames:
            p = (frame.frame_path or "").replace("\\", "/")
            if p.startswith("app/static/"):
                p = p[len("app/static/"):]
            elif p.startswith("static/"):
                p = p[len("static/"):]
            frame.frame_path = p
        
        return render_template("video_status.html", video=video, frames=frames)
        
    except Exception as e:
        flash(f"Error loading video status: {str(e)}", "error")
        return redirect(url_for("upload.video_upload"))
        
    finally:
        session.close()

@upload_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Display a dashboard with processing statistics and system status.
    """
    session = SessionLocal()
    
    try:
        # Get user's videos
        videos = session.query(SurfVideo).filter_by(user_id=current_user.id).all()
        
        # Get user's frames
        frames = session.query(SurferFrame).filter_by(user_id=current_user.id).all()
        
        # Calculate statistics
        stats = {
            'total_videos': len(videos),
            'total_frames': len(frames),
            'videos_by_status': {},
            'avg_score': 0,
            'high_confidence_frames': 0,
            'processing_time': {},
        }
        
        # Count videos by status
        for video in videos:
            status = video.status
            if status in stats['videos_by_status']:
                stats['videos_by_status'][status] += 1
            else:
                stats['videos_by_status'][status] = 1
        
        # Calculate average score and high confidence frames
        if frames:
            total_score = sum(frame.score for frame in frames)
            stats['avg_score'] = total_score / len(frames)
            stats['high_confidence_frames'] = sum(1 for frame in frames if frame.score >= 0.9)
        
        # Calculate processing times and rates
        for video in videos:
            if video.status == 'completed' and video.frame_count and video.processed_frames:
                # Calculate processing time (if we had created_at and updated_at)
                if hasattr(video, 'created_at') and hasattr(video, 'updated_at'):
                    processing_time = (video.updated_at - video.created_at).total_seconds()
                    stats['processing_time'][video.id] = processing_time
                
                # Calculate detection rate
                detection_rate = video.processed_frames / video.frame_count
                if 'detection_rate' not in stats:
                    stats['detection_rate'] = []
                stats['detection_rate'].append(detection_rate)
        
        # Calculate average detection rate
        if 'detection_rate' in stats and stats['detection_rate']:
            stats['avg_detection_rate'] = sum(stats['detection_rate']) / len(stats['detection_rate'])
        else:
            stats['avg_detection_rate'] = 0
        
        # Get recent activity (last 5 videos)
        recent_videos = session.query(SurfVideo).filter_by(user_id=current_user.id).order_by(SurfVideo.id.desc()).limit(5).all()
        
        return render_template(
            "dashboard.html",
            stats=stats,
            videos=videos,
            recent_videos=recent_videos
        )
        
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "error")
        return redirect(url_for("upload.profile"))
        
    finally:
        session.close()

@upload_bp.route("/video/<int:video_id>/process")
@login_required
def process_video_route(video_id):
    """
    Trigger the processing of a video.
    """
    session = SessionLocal()
    
    try:
        # Get the video
        video = session.query(SurfVideo).filter_by(id=video_id, user_id=current_user.id).first()
        
        if not video:
            flash("Video not found or you don't have permission to process it.", "error")
            return redirect(url_for("upload.video_upload"))
            
        # Check if the video is already being processed
        if video.status == "processing":
            flash("This video is already being processed.", "warning")
            return redirect(url_for("upload.video_status", video_id=video_id))
            
        # Check if the video has already been processed
        if video.status == "completed":
            flash("This video has already been processed.", "warning")
            return redirect(url_for("upload.video_status", video_id=video_id))
            
        # Queue the video processing task in Celery
        enqueue_process_video(video_id)
        
        flash("Video processing has started. This may take several minutes.", "success")
        return redirect(url_for("upload.video_status", video_id=video_id))
        
    except Exception as e:
        flash(f"Error starting video processing: {str(e)}", "error")
        return redirect(url_for("upload.video_status", video_id=video_id))
        
    finally:
        session.close()
