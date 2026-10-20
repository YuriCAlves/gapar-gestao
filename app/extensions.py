from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Configuração do Flask-Login
login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor, faça login com sua conta Google autorizada para acessar o sistema."
login_manager.login_message_category = "warning"
