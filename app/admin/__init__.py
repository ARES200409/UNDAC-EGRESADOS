# app/admin/__init__.py
from flask import Blueprint

admin = Blueprint('admin', __name__)

from app.admin import egresados
from app.admin import empresas
from app.admin import ofertas
from app.admin import personal
from app.admin import dashboard
from app.admin import encuestas
from app.admin import catalogos
from app.admin import empleabilidad
from app.admin import campanas
from app.admin import reportes
from app.admin import auditoria
