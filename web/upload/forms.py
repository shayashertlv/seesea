from flask_wtf import FlaskForm
from wtforms import MultipleFileField, SubmitField
from wtforms.validators import DataRequired

class UploadImagesForm(FlaskForm):
    images = MultipleFileField("Choose image(s)", validators=[DataRequired()])
    submit = SubmitField("Upload")
