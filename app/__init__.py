import json
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
    from .blueprints.avisos import avisos_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(animals_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(adoptions_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(avisos_bp)

    # RNF05/RN12: toda a API interna exige sessão ativa. A trava é central para que nenhuma rota
    # nova fique aberta por esquecimento. As rotas /auth/* ficam fora, pois fazem o próprio login.
    @app.before_request
    def require_authenticated_api():
        from flask import request
        from flask_login import current_user
        if request.path.startswith("/api/") and not current_user.is_authenticated:
            return jsonify({
                "erro": "Não autorizado",
                "mensagem": "Autenticação obrigatória via Google OAuth e Whitelist (RF01/RF02)."
            }), 401

    # RN14: revogação com efeito imediato na próxima requisição
    @app.before_request
    def enforce_whitelist_status():
        from flask_login import current_user, logout_user
        if current_user.is_authenticated and not current_user.is_active:
            logout_user()
            return jsonify({
                "erro": "Acesso revogado",
                "mensagem": "Seu e-mail foi desativado na Whitelist pela administração (RN12/RN14)."
            }), 403

    # Respostas de erro sempre em JSON no formato {"erro", "codigo", "mensagem"}
    from .utils.validation import ApiError

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(error.to_response()[0]), error.status

    @app.after_request
    def normalize_error_body(response):
        """Garante `erro` + `codigo` em toda resposta JSON de erro (aceita o legado `error`)."""
        if response.status_code >= 400 and response.is_json:
            body = response.get_json(silent=True)
            if isinstance(body, dict):
                if "error" in body and "erro" not in body:
                    body["erro"] = body.pop("error")
                body.setdefault("erro", "Erro")
                body["codigo"] = response.status_code
                response.set_data(json.dumps(body, ensure_ascii=False))
        return response

    def _json_error(status, erro, mensagem):
        return jsonify({"erro": erro, "codigo": status, "mensagem": mensagem}), status

    @app.errorhandler(400)
    def bad_request_error(error):
        return _json_error(400, "Requisição inválida", getattr(error, "description", "Parâmetros inválidos"))

    @app.errorhandler(401)
    def unauthorized_error(error):
        return _json_error(401, "Não autorizado", "Autenticação obrigatória via Google OAuth e Whitelist (RF01/RF02).")

    @app.errorhandler(403)
    def forbidden_error(error):
        return _json_error(403, "Acesso proibido", "Você não tem permissão para acessar este recurso.")

    @app.errorhandler(404)
    def not_found_error(error):
        return _json_error(404, "Recurso não encontrado", "A rota ou registro solicitado não existe.")

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return _json_error(405, "Método não permitido", "Este método HTTP não é aceito nesta rota.")

    @app.errorhandler(413)
    def too_large_error(error):
        return _json_error(413, "Arquivo muito grande", "O arquivo enviado excede o limite de 10 MB.")

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return _json_error(500, "Erro interno do servidor", "Ocorreu um erro inesperado no processamento.")

    from .commands import create_admin, seed_data
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_data)

    return app
