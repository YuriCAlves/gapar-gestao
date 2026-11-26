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


# SDD v5.1 (R8): o SQLite só confere chaves estrangeiras com `PRAGMA foreign_keys = ON`, por
# conexão. Sem isso os testes aceitariam FK órfã que o PostgreSQL de produção recusa.
from sqlalchemy import event as _event
from sqlalchemy.engine import Engine as _Engine


@_event.listens_for(_Engine, "connect")
def _sqlite_com_chaves_estrangeiras(conexao_dbapi, _registro):
    import sqlite3
    if isinstance(conexao_dbapi, sqlite3.Connection):
        cursor = conexao_dbapi.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
