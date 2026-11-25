"""Servicio centralizado de auditoría y trazabilidad persistente en MySQL."""

from flask import request, current_app
from flask_login import current_user
from app.extensions import db
from app.models import Auditoria


def registrar_auditoria(
    accion,
    modulo,
    entidad=None,
    id_registro=None,
    resultado='exito',
    detalle=None,
    id_usuario=None,
):
    """Registra una acción relevante en la tabla `auditoria`.

    Nunca almacena contraseñas ni payloads sensibles. Si ocurre un error de BD
    al escribir la bitácora, hace rollback de la sesión de auditoría sin
    interrumpir la operación principal.
    """
    try:
        uid = id_usuario
        if uid is None and getattr(current_user, 'is_authenticated', False):
            uid = getattr(current_user, 'id_usuario', None)

        ip = None
        if request:
            ip = (request.remote_addr or '')[:45] or None

        registro = Auditoria(
            id_usuario=uid,
            accion=str(accion or '')[:80],
            modulo=str(modulo or '')[:60],
            entidad=str(entidad)[:60] if entidad else None,
            id_registro=str(id_registro)[:60] if id_registro is not None else None,
            resultado=resultado if resultado in ('exito', 'denegado', 'error') else 'exito',
            detalle=str(detalle)[:500] if detalle else None,
            ip_origen=ip,
        )
        db.session.add(registro)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        if current_app:
            current_app.logger.warning('No se pudo persistir evento de auditoría: %s/%s', modulo, accion)
