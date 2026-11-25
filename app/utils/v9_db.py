"""Activación progresiva de V9. La ausencia de migración no rompe V8."""
from sqlalchemy import inspect
from app.extensions import db

def tablas_v9_disponibles():
    try:
        return inspect(db.engine).has_table('seguimiento_externo')
    except Exception:
        return False
