# app/upload/routes.py

import os
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.upload import upload_bp
from app.upload.forms import UploadForm
from app.tasks.embed import generate_face_embedding

UPLOAD_FOLDER = "app/static/uploads"

@upload_bp.route("/", methods=["GET", "POST"])
@login_required
def upload_page():
    form = UploadForm()
    if form.validate_on_submit():
        face_file = form.face_image.data
        board_file = form.board_image.data

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        face_filename = secure_filename(f"{current_user.username}_face.jpg")
        board_filename = secure_filename(f"{current_user.username}_board.jpg")

        face_path = os.path.join(UPLOAD_FOLDER, face_filename)
        board_path = os.path.join(UPLOAD_FOLDER, board_filename)

        face_file.save(face_path)
        board_file.save(board_path)

        # Generate face embedding (we'll define this next)
        generate_face_embedding(current_user.id, face_path)

        flash("Images uploaded and embedding generated!")
        return redirect(url_for("upload.upload_page"))

    return render_template("upload.html", form=form)

@upload_bp.route("/gallery")
@login_required
def gallery():
    from app.database import SessionLocal
    from app.models import SurferFrame

    session = SessionLocal()
    frames = session.query(SurferFrame).filter_by(user_id=current_user.id).all()
    session.close()

    return render_template("gallery.html", frames=frames)
