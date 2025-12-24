from flask import Blueprint, redirect, url_for, render_template
from flask_login import login_required

bp = Blueprint("home", __name__, url_prefix="")

@bp.get("/")
def root():
    return redirect(url_for("auth.login"))

@bp.get("/home")
@login_required
def index():
    return render_template("home/index.html")