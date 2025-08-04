# app/upload/video_forms.py

from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, TextAreaField
from wtforms.validators import Optional, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired

class VideoUploadForm(FlaskForm):
    """Form for uploading surf videos for processing."""
    
    video_file = FileField(
        "Surf Video",
        validators=[
            FileRequired(message="Please select a video file to upload"),
            FileAllowed(['mp4', 'mov', 'avi'], 'Video files only (MP4, MOV, AVI)!')
        ],
        description="Upload a video of surfers in action. Maximum size: 500MB."
    )
    
    location = StringField(
        "Beach Location",
        validators=[Optional(), Length(max=100)],
        description="Where was this video recorded? (e.g., 'Pipeline, North Shore')"
    )
    
    description = TextAreaField(
        "Video Description",
        validators=[Optional(), Length(max=500)],
        description="Add any additional details about this surf session."
    )
    
    submit = SubmitField("Upload Video for Processing")