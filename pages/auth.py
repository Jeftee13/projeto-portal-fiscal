from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from extensions import db
from models import User

bp = Blueprint("auth", __name__, url_prefix="")

@bp.get("/login")
def login():
    return render_template("auth/login.html")

@bp.post("/login")
def login_post():
    email = request.form.get("email","").strip().lower()
    password = request.form.get("password","")

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user.password_hash, password):
        flash("Senha inválida.", "danger")
        return redirect(url_for("auth.login"))

    if user.status == "PENDING":
        return redirect(url_for("auth.pending"))

    if user.status == "REJECTED":
        flash("Cadastro rejeitado. Procure o administrador.", "warning")
        return redirect(url_for("auth.login"))

    login_user(user)
    return redirect(url_for("home.index"))

@bp.get("/register")
def register():
    return render_template("auth/register.html")

@bp.post("/register")
def register_post():
    nome = request.form.get("nome","").strip()
    email = request.form.get("email","").strip().lower()
    password = request.form.get("password","")

    if not nome or not email or not password:
        flash("Preencha todos os campos.", "danger")
        return redirect(url_for("auth.register"))

    if User.query.filter_by(email=email).first():
        flash("E-mail já cadastrado.", "warning")
        return redirect(url_for("auth.register"))

    user = User(
        nome=nome,
        email=email,
        password_hash=generate_password_hash(password),
        status="PENDING",
        role="USER",
    )
    db.session.add(user)
    db.session.commit()

    return redirect(url_for("auth.pending"))

@bp.get("/pending")
def pending():
    return render_template("auth/pending.html")

@bp.get("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))