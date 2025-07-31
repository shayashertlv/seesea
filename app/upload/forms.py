# app/upload/forms.py

from flask_wtf import FlaskForm
from wtforms import SubmitField
from flask_wtf.file import FileField, FileAllowed, FileRequired

class UploadForm(FlaskForm):
    face_image = FileField(
        "Face Image",
        validators=[FileRequired(), FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')]
    )
    board_image = FileField(
        "Surfboard Image",
        validators=[FileRequired(), FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')]
    )
    submit = SubmitField("Upload")
