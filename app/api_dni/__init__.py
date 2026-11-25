# app/api_dni/__init__.py
from flask import Blueprint

api_dni = Blueprint('api_dni', __name__, url_prefix='/api')
