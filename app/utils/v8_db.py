"""Activación gradual para no interrumpir el sistema si no se ejecutó la migración."""
from sqlalchemy import inspect
from app.extensions import db


def tablas_v8_disponibles():
    try:
        inspector = inspect(db.engine)
        return inspector.has_table('postulaciones') and inspector.has_table('ofertas_guardadas')
    except Exception:
        # No reemplaza monitoreo de base de datos; evita un 500 por migración pendiente.
        return False
