from flask import Blueprint

health_bp = Blueprint("health", __name__, url_prefix="/saude")

from . import routes
