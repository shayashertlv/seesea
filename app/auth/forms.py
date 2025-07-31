# app/auth/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length

class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=30)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=6, max=100)])
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=30)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=6, max=100)])
    submit = SubmitField("Login")
