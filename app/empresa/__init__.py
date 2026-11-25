from flask import Blueprint

empresa = Blueprint('empresa', __name__)

from app.empresa import routes  # noqa: E402, F401
