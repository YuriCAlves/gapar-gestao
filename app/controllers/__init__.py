"""Camada Controller (MVC): recebe a requisição HTTP, aplica as regras e devolve JSON.

Cada módulo `*_controller.py` define um Blueprint Flask responsável por um recurso da API.
"""
from .admin_controller import admin_bp
from .adoptions_controller import adoptions_bp
from .animals_controller import animals_bp
from .auth_controller import auth_bp
from .avisos_controller import avisos_bp
from .core_controller import core_bp
from .health_controller import health_bp
from .inventory_controller import inventory_bp
from .isolation_controller import isolation_bp
from .og_controller import og_bp
from .public_controller import public_bp

BLUEPRINTS = (auth_bp, core_bp, animals_bp, health_bp, adoptions_bp, admin_bp, avisos_bp, public_bp, og_bp,
              inventory_bp, isolation_bp)


def register_controllers(app):
    """Registra todos os controllers (Blueprints) na aplicação Flask."""
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
