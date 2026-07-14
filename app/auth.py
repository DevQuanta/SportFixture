from flask import Blueprint, render_template, url_for, redirect, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import select
from .models import Admin
from .database import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods = ["GET", "POST"]) # type: ignore
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.knockouts_page'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        stmt = select(Admin).where(Admin.email == email)
        admin = db.session.execute(stmt).scalar_one_or_none()

        if admin and admin.check_password(password):
            login_user(admin)

            return redirect(url_for('main.knockouts_page'))

        error_msg = "Invalid email or password."

        return render_template("login.html", error=error_msg), 400

    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
