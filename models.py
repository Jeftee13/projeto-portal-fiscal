from extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # status: PENDING / ACTIVE / REJECTED
    status = db.Column(db.String(20), nullable=False, default="PENDING")

    # role: ADMIN / USER
    role = db.Column(db.String(20), nullable=False, default="USER")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_admin(self) -> bool:
        return self.role == "ADMIN"


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(14), nullable=False, unique=True)  # só números
    regime_tributario = db.Column(db.String(60), nullable=False)
    responsavel_fiscal = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Este é o campo que guardará todo o texto, imagens e GIFs do manual
    manual_content = db.Column(db.Text, nullable=True)