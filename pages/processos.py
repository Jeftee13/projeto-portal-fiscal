from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("processos", __name__, url_prefix="/processos")

@bp.get("/")
@login_required
def index():
    return render_template("processos/index.html")