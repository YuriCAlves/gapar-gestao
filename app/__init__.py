import json
import os
from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import ProductionConfig, config_by_name
from .extensions import db, migrate, login_manager


def create_app(config_name=None):
    """Fábrica da aplicação Flask para o Back-end GAPAR Gestão."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    if config_class is ProductionConfig:
        # Falha cedo e com mensagem clara, em vez de subir com chave padrão ou sem banco.
        problemas = ProductionConfig.problemas(app.config)
        if problemas:
            raise RuntimeError("Configuração de produção incompleta: " + " ".join(problemas))
        if not (app.config.get("SUPABASE_URL") and app.config.get("SUPABASE_SERVICE_ROLE_KEY")):
            app.logger.warning("Supabase Storage não configurado: fotos irão para disco temporário e serão perdidas.")
        # A Vercel encerra o HTTPS e repassa protocolo/host/IP nos cabeçalhos X-Forwarded-*.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Inicializa extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)


    from . import models

    
    # Diretório para uploads / arquivos do sistema
    upload_path = app.config.get("UPLOAD_FOLDER")
    if upload_path:
        os.makedirs(upload_path, exist_ok=True)

    # Registra os Controllers (Blueprints da API)
    from .controllers import register_controllers

    register_controllers(app)

    # RNF05/RN12: toda a API interna exige sessão ativa. A trava é central para que nenhuma rota
    # nova fique aberta por esquecimento. As rotas /auth/* ficam fora, pois fazem o próprio login.
    @app.before_request
    def require_authenticated_api():
        from flask import request, g
        from flask_login import current_user, logout_user
        if request.path.startswith("/api/") and not current_user.is_authenticated:
            if g.get("acesso_revogado"):
                logout_user()  # encerra a sessão: as próximas requisições recebem 401
                return jsonify({
                    "erro": "Acesso revogado",
                    "mensagem": "Seu e-mail foi desativado na Whitelist pela administração (RN12/RN14)."
                }), 403
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
        # Descarta alterações pela metade (ex.: campos já atribuídos antes de a validação falhar)
        db.session.rollback()
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

    # Rede de segurança: uma restrição do banco (UNIQUE, CHECK, chave estrangeira, tamanho de
    # coluna) violada por uma corrida ou por um dado que escapou da validação vira resposta JSON
    # clara, e não um erro 500. O detalhe técnico fica só no log do servidor.
    from sqlalchemy.exc import DataError, IntegrityError

    from .models.base import AuditoriaImutavel, ExclusaoFisicaProibida

    @app.errorhandler(ExclusaoFisicaProibida)
    def physical_delete_error(error):
        db.session.rollback()
        app.logger.warning("Exclusão física bloqueada: %s", error)
        return _json_error(422, "Exclusão não permitida",
                           "Registros de animais, prontuários e vacinas não podem ser apagados; use a exclusão lógica (RN03).")

    @app.errorhandler(AuditoriaImutavel)
    def immutable_audit_error(error):
        db.session.rollback()
        app.logger.warning("Alteração da auditoria bloqueada: %s", error)
        return _json_error(422, "Auditoria imutável",
                           "A trilha de auditoria não pode ser alterada nem apagada (RN16).")

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        db.session.rollback()
        app.logger.warning("Violação de integridade no banco: %s", getattr(error, "orig", error))
        # 23001 (restrict_violation): gatilhos do PostgreSQL que protegem RN03 e RN16
        if getattr(getattr(error, "orig", None), "pgcode", None) == "23001":
            return _json_error(422, "Operação não permitida",
                               "Este registro é protegido: não pode ser apagado nem alterado (RN03, RN16).")
        return _json_error(409, "Conflito de dados",
                           "Estes dados conflitam com um registro já existente ou com uma regra do cadastro. "
                           "Atualize a tela, confira as informações e tente novamente.")

    @app.errorhandler(DataError)
    def data_error(error):
        db.session.rollback()
        app.logger.warning("Dado recusado pelo banco: %s", getattr(error, "orig", error))
        return _json_error(400, "Dados inválidos",
                           "Algum campo tem valor ou tamanho que o cadastro não aceita. Confira as informações e tente novamente.")

    from .commands import create_admin, seed_data
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_data)

    return app
