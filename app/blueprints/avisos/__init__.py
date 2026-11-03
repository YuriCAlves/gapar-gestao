from flask import Blueprint

avisos_bp = Blueprint("avisos", __name__, url_prefix="/api/avisos")

from . import routes
