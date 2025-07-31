# app/auth/routes.py

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.auth.forms import RegisterForm, LoginForm
from app.models import User
from app.database import SessionLocal
from werkzeug.security import generate_password_hash, check_password_hash


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        session = SessionLocal()
        existing_user = session.query(User).filter_by(username=form.username.data).first()
        if existing_user:
            flash("User already exists.")
        else:
            new_user = User(
                username=form.username.data,
                password=generate_password_hash(form.password.data)
            )
            session.add(new_user)
            session.commit()
            flash("User registered! You can now log in.")
            return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = SessionLocal()
        user = session.query(User).filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Logged in successfully.")
            return redirect(url_for("auth.login"))  # Change this later to upload.upload_page
        else:
            flash("Invalid credentials.")
    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.")
    return redirect(url_for("auth.login"))
