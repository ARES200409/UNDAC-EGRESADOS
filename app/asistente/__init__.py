from flask import Blueprint
asistente = Blueprint('asistente', __name__, url_prefix='/asistente')
from app.asistente import routes
