from flask import Blueprint

adoptions_bp = Blueprint("adoptions", __name__, url_prefix="/adocoes")

from . import routes
