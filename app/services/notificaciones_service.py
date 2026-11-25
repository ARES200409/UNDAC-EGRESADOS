"""Servicio para emitir y consultar notificaciones internas en la plataforma."""

from datetime import datetime, timezone
from flask import current_app
from app.extensions import db
from app.models import Notificaciones


def crear_notificacion(id_usuario, titulo, mensaje, tipo='sistema', enlace=None):
    """Crea una notificación interna para un usuario sin interrumpir el flujo principal."""
    if not id_usuario:
        return None
    try:
        notif = Notificaciones(
            id_usuario=id_usuario,
            tipo=str(tipo or 'sistema')[:40],
            titulo=str(titulo or '')[:180],
            mensaje=str(mensaje or '')[:500],
            enlace=str(enlace)[:255] if enlace else None,
            leida=0,
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        if current_app:
            current_app.logger.warning('No se pudo crear notificación para usuario %s', id_usuario)
        return None


def contar_no_leidas(id_usuario):
    """Devuelve el conteo de notificaciones no leídas de un usuario."""
    if not id_usuario:
        return 0
    return Notificaciones.query.filter_by(id_usuario=id_usuario, leida=0).count()


def marcar_como_leida(id_notificacion, id_usuario):
    """Marca una notificación propia como leída."""
    n = Notificaciones.query.filter_by(id_notificacion=id_notificacion, id_usuario=id_usuario).first()
    if n and not n.leida:
        n.leida = 1
        n.leida_en = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
    return n
