from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()



@login_manager.unauthorized_handler
def unauthorized():
    """API JSON pura: sem redirecionamento para página de login (o SPA trata o 401)."""
    from flask import jsonify
    return jsonify({
        "error": "Não autorizado",
        "mensagem": "Autenticação obrigatória via Google OAuth e Whitelist (RF01/RF02)."
    }), 401
