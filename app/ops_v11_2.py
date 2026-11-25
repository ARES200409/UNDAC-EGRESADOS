"""Endpoints de salud: no incluyen datos personales ni credenciales."""
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db

ops = Blueprint('nexo_ops_v11_2', __name__)

def _comprobar_db():
    # SELECT 1 evita cambiar registros o requerir permisos de escritura.
    db.session.execute(text('SELECT 1')).scalar()

@ops.get('/health/live')
def salud_proceso():
    return jsonify(service='nexo-undac', status='ok'), 200

@ops.get('/health/ready')
def salud_dependencias():
    try:
        _comprobar_db()
        return jsonify(service='nexo-undac', status='ready'), 200
    except SQLAlchemyError:
        current_app.logger.warning('readiness: fallo de conexion a la base de datos')
    except Exception:
        current_app.logger.exception('readiness: fallo interno no esperado')
    return jsonify(service='nexo-undac', status='unavailable'), 503
