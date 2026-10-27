import os
import logging
from flask import Flask
from .config import Config
from .extensions import db, jwt, bcrypt

logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(root, 'templates'),
        static_folder=os.path.join(root, 'static'),
    )
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # Registrar blueprints ANTES de db.create_all() para que todos los modelos
    # estén importados cuando SQLAlchemy cree las tablas.
    from . import models  # noqa: F401 — asegura que los modelos se registren

    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from .quizzes import quizzes_bp
    app.register_blueprint(quizzes_bp, url_prefix='/api/quizzes')

    from .public import public_bp
    app.register_blueprint(public_bp)

    from .admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    try:
        from .rag import rag_bp
        app.register_blueprint(rag_bp, url_prefix='/api/rag')
    except Exception as e:
        logger.warning(f"RAG blueprint not loaded: {e}")

    with app.app_context():
        db.create_all()

    return app
