# app/egresado/__init__.py
from flask import Blueprint

egresado = Blueprint('egresado', __name__)

from app.egresado import routes
from app.egresado import seguimiento