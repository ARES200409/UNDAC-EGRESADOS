from flask import Blueprint

documentos = Blueprint('documentos', __name__)

from app.documentos import routes  # noqa: E402, F401
