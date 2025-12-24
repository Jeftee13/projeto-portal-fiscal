from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import User

bp = Blueprint("admin", __name__, url_prefix="/admin")

def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin():
        flash("Acesso restrito ao administrador.", "warning")
        return False
    return True

@bp.get("/pending-users")
@login_required
def pending_users():
    if not admin_required():
        return redirect(url_for("home.index"))
    users = User.query.filter_by(status="PENDING").order_by(User.created_at.desc()).all()
    return render_template("admin/pending.html", users=users)

@bp.get("/approve/<int:user_id>")
@login_required
def approve_user(user_id):
    if not admin_required():
        return redirect(url_for("home.index"))
    user = User.query.get_or_404(user_id)
    user.status = "ACTIVE"
    db.session.commit()
    flash("Usuário aprovado.", "success")
    return redirect(url_for("admin.pending_users"))

@bp.get("/reject/<int:user_id>")
@login_required
def reject_user(user_id):
    if not admin_required():
        return redirect(url_for("home.index"))
    user = User.query.get_or_404(user_id)
    user.status = "REJECTED"
    db.session.commit()
    flash("Usuário rejeitado.", "info")
    return redirect(url_for("admin.pending_users"))