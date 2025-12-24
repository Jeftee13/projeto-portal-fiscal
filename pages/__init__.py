from .auth import bp as auth_bp
from .home import bp as home_bp
from .processos import bp as processos_bp
from .admin import bp as admin_bp
from .manual import bp as manual_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(processos_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(manual_bp)