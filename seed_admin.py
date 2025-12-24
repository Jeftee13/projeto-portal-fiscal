from werkzeug.security import generate_password_hash
from app import create_app
from extensions import db
from models import User

app = create_app()

with app.app_context():
    email = "admin@seuescritorio.com"
    if not User.query.filter_by(email=email).first():
        u = User(
            nome="Administrador",
            email=email,
            password_hash=generate_password_hash("Admin@123"),
            status="ACTIVE",
            role="ADMIN"
        )
        db.session.add(u)
        db.session.commit()
        print("Admin criado:", email, "senha: Admin@123")
    else:
        print("Admin já existe.")