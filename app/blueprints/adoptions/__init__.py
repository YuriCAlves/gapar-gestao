from flask import Blueprint

adoptions_bp = Blueprint("adoptions", __name__, url_prefix="/api/adocoes")

from . import routes
