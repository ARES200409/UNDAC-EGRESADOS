"""Visor administrativo de registros persistentes de auditoría."""

from datetime import datetime, time
from flask import render_template, request, flash
from flask_login import login_required

from app.admin import admin
from app.admin.helpers import requiere_rol
from app.extensions import db
from app.models import Auditoria, Usuarios
from app.services.validaciones_service import limpiar_texto, parse_fecha_iso


@admin.route('/admin/auditoria')
@login_required
@requiere_rol('administrador', 'utsag')
def visor_auditoria():
    modulo = limpiar_texto(request.args.get('modulo'), 60)
    accion = limpiar_texto(request.args.get('accion'), 80)
    resultado = limpiar_texto(request.args.get('resultado'), 20)
    correo = limpiar_texto(request.args.get('correo'), 120)
    page = request.args.get('page', 1, type=int)

    fecha_desde = None
    fecha_hasta = None
    try:
        fecha_desde = parse_fecha_iso(request.args.get('fecha_desde'), obligatoria=False)
        fecha_hasta = parse_fecha_iso(request.args.get('fecha_hasta'), obligatoria=False)
    except ValueError as exc:
        flash(str(exc), 'warning')

    q = Auditoria.query.outerjoin(Usuarios, Auditoria.id_usuario == Usuarios.id_usuario)
    if modulo:
        q = q.filter(Auditoria.modulo == modulo)
    if accion:
        q = q.filter(Auditoria.accion.ilike(f'%{accion}%'))
    if resultado in ('exito', 'denegado', 'error'):
        q = q.filter(Auditoria.resultado == resultado)
    if correo:
        q = q.filter(Usuarios.correo.ilike(f'%{correo}%'))
    if fecha_desde:
        q = q.filter(Auditoria.creado_en >= datetime.combine(fecha_desde, time.min))
    if fecha_hasta:
        q = q.filter(Auditoria.creado_en <= datetime.combine(fecha_hasta, time.max))

    paginacion = q.add_columns(Usuarios.correo).order_by(Auditoria.creado_en.desc()).paginate(
        page=max(1, page), per_page=50, error_out=False
    )

    modulos_disponibles = [
        m[0] for m in db.session.query(Auditoria.modulo).distinct().order_by(Auditoria.modulo).all()
        if m[0]
    ]
    resumen = {
        'exito': Auditoria.query.filter_by(resultado='exito').count(),
        'denegado': Auditoria.query.filter_by(resultado='denegado').count(),
        'error': Auditoria.query.filter_by(resultado='error').count(),
    }

    return render_template(
        'admin/auditoria.html',
        registros=paginacion.items,
        paginacion=paginacion,
        modulos_disponibles=modulos_disponibles,
        resumen=resumen,
        filtros={
            'modulo': modulo,
            'accion': accion,
            'resultado': resultado,
            'correo': correo,
            'fecha_desde': fecha_desde.isoformat() if fecha_desde else '',
            'fecha_hasta': fecha_hasta.isoformat() if fecha_hasta else '',
        },
    )
