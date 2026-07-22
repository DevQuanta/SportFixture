# app/__init__.py
from flask import Flask, make_response
import json
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from .database import db, migrate
from flask_login import LoginManager
from .models import Admin
from app.exceptions import DomainError

login_manager = LoginManager()

def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Prevents memory overhead
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SECRET_KEY'] = "423065c1c9051794762810b2cf8ffec2"


    # Connect DB to App
    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()

    login_manager.login_view = "auth.login" # type: ignore

    @login_manager.user_loader
    def load_user(user_id):
        stmt = select(Admin).where(Admin.id == user_id)
        return db.session.execute(stmt).scalar_one_or_none()

    from app.auth import auth_bp
    from app.blueprints.admin.routes import admin
    from app.blueprints.api.routes import api
    from app.blueprints.public.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api)
    app.register_blueprint(admin)

    @app.errorhandler(DomainError)
    def handle_domain_error(error):
        """
        Catches any DomainError
        """
        response = make_response(error.message, 422)

        response.headers["HX-Trigger"] = json.dumps({
            "toast": {
                "message": error.message,
                "type": "error"
            }
        })
        return response

    return app
