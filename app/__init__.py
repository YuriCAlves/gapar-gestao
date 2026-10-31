import os
from flask import Flask, jsonify
from .config import config_by_name
from .extensions import db, migrate, login_manager


def create_app(config_name=None):
    """Fábrica da aplicação Flask para o Back-end GAPAR Gestão."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Inicializa extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)


    from . import models

    
    # Diretório para uploads / arquivos do sistema
    upload_path = app.config.get("UPLOAD_FOLDER")
    if upload_path:
        os.makedirs(upload_path, exist_ok=True)

    # Registra Blueprints (Back-end)
    from .blueprints.auth import auth_bp
    from .blueprints.core import core_bp
    from .blueprints.animals import animals_bp
    from .blueprints.health import health_bp
    from .blueprints.adoptions import adoptions_bp
    from .blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(animals_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(adoptions_bp)
    app.register_blueprint(admin_bp)

    # Handlers de erro no padrão JSON (Back-end / APIs)
    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            "error": "Requisição inválida",
            "detalhes": str(error.description) if hasattr(error, 'description') else "Parâmetros inválidos"
        }), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        return jsonify({
            "error": "Não autorizado",
            "mensagem": "Autenticação obrigatória via Google OAuth e Whitelist (RF01/RF02)."
        }), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({
            "error": "Acesso proibido",
            "mensagem": "Você não tem permissão para acessar este recurso."
        }), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": "Recurso não encontrado",
            "mensagem": "A rota ou registro solicitado não existe."
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({
            "error": "Erro interno do servidor",
            "mensagem": "Ocorreu um erro inesperado no processamento."
        }), 500

    return app
