#auth/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from .. import db
from ..models import User
from .forms import RegisterForm, LoginForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/ping")
def ping():
    return "auth blueprint alive"

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered", "warning")
            return redirect(url_for("auth.register"))
        user = User(email=form.email.data,
                    password_hash=generate_password_hash(form.password.data))
        db.session.add(user); db.session.commit()
        flash("Account created, please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)

# web/auth/routes.py  – inside the login() view
from flask import request

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    # 👉 allow someone who is already logged-in to skip the form
    if current_user.is_authenticated:                       # add this line
        return redirect(url_for("upload.index"))

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)

            # respect ?next=… param so we return where @login_required sent us
            next_page = request.args.get("next")
            return redirect(next_page or url_for("upload.index"))

        flash("Invalid credentials", "danger")

    return render_template("auth/login.html", form=form)



@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
