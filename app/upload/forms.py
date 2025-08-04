# app/upload/forms.py

from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, TextAreaField
from wtforms.validators import Optional, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired

class UploadForm(FlaskForm):
    face_image = FileField(
        "Face Image (Front View)",
        validators=[
            FileRequired(message="Please upload a clear front-facing photo"),
            FileAllowed(['jpg', 'png', 'jpeg'], 'Images only (JPG, PNG, JPEG)!')
        ],
        description="Upload a clear, well-lit photo of your face looking directly at the camera. This helps us identify you in surfing photos."
    )
    
    face_image_side = FileField(
        "Face Image (Side View, Optional)",
        validators=[
            FileAllowed(['jpg', 'png', 'jpeg'], 'Images only (JPG, PNG, JPEG)!')
        ],
        description="An optional side profile photo can improve recognition accuracy."
    )
    
    board_image = FileField(
        "Surfboard Image",
        validators=[
            FileRequired(message="Please upload a photo of your surfboard"),
            FileAllowed(['jpg', 'png', 'jpeg'], 'Images only (JPG, PNG, JPEG)!')
        ],
        description="Upload a clear photo of your surfboard. Include any distinctive features, colors, or patterns."
    )
    
    wetsuit_description = TextAreaField(
        "Wetsuit Description (Optional)",
        validators=[Optional(), Length(max=200)],
        description="Describe your wetsuit color and any distinctive features to help with identification."
    )
    
    submit = SubmitField("Upload Reference Images")
