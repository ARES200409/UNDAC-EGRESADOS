"""Rutas para gestión de capacitaciones, eventos, inscripciones, constancias y notificaciones."""

import secrets
from datetime import datetime, timezone
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.capacitaciones import capacitaciones
from app.admin.helpers import requiere_rol
from app.extensions import db
from app.models import Capacitaciones, InscripcionesCapacitacion, Egresados, Notificaciones, Usuarios
from app.services.validaciones_service import limpiar_texto, parse_fecha_iso, entero_en_rango
from app.services.auditoria_service import registrar_auditoria
from app.services.notificaciones_service import crear_notificacion, marcar_como_leida

TIPOS_CAPACITACION = [
    ('curso', 'Curso'),
    ('taller', 'Taller'),
    ('seminario', 'Seminario'),
    ('conferencia', 'Conferencia'),
    ('congreso', 'Congreso'),
    ('feria_laboral', 'Feria laboral'),
    ('networking', 'Networking'),
    ('otro', 'Otro'),
]
TIPOS_DICT = dict(TIPOS_CAPACITACION)
MODALIDADES_CAP = ('presencial', 'virtual', 'hibrido')
ESTADOS_CAP = ('borrador', 'publicada', 'finalizada', 'cancelada')
ESTADOS_INSC = ('inscrito', 'asistio', 'no_asistio', 'cancelado')


def _cupos_ocupados(id_capacitacion):
    return InscripcionesCapacitacion.query.filter(
        InscripcionesCapacitacion.id_capacitacion == id_capacitacion,
        InscripcionesCapacitacion.estado.in_(['inscrito', 'asistio']),
    ).count()


def _es_ruta_interna_segura(enlace):
    texto = str(enlace or '').strip()
    return texto.startswith('/') and not texto.startswith('//')


# ============================================================
# EGRESADO: CATÁLOGO E INSCRIPCIONES
# ============================================================
@capacitaciones.route('/capacitaciones')
@login_required
def catalogo_egresado():
    if not current_user.es_egresado():
        abort(403)
    tipo_filtro = limpiar_texto(request.args.get('tipo'), 30)
    q = Capacitaciones.query.filter(Capacitaciones.estado == 'publicada')
    if tipo_filtro in TIPOS_DICT:
        q = q.filter(Capacitaciones.tipo == tipo_filtro)
    lista = q.order_by(Capacitaciones.fecha_inicio.asc()).all()

    mis_inscripciones = {
        ins.id_capacitacion: ins
        for ins in InscripcionesCapacitacion.query.filter_by(id_egresado=current_user.id_egresado).all()
    }
    ocupados = {c.id_capacitacion: _cupos_ocupados(c.id_capacitacion) for c in lista}

    return render_template(
        'capacitaciones/egresado_lista.html',
        capacitaciones_lista=lista,
        mis_inscripciones=mis_inscripciones,
        ocupados=ocupados,
        tipos=TIPOS_CAPACITACION,
        tipos_dict=TIPOS_DICT,
        tipo_filtro=tipo_filtro,
    )


@capacitaciones.route('/capacitaciones/<int:id_capacitacion>/inscribirse', methods=['POST'])
@login_required
def inscribirse(id_capacitacion):
    if not current_user.es_egresado():
        abort(403)
    cap = db.session.get(Capacitaciones, id_capacitacion)
    if not cap:
        abort(404)
    if cap.estado != 'publicada':
        flash('Esta capacitación no acepta inscripciones actualmente.', 'warning')
        return redirect(url_for('capacitaciones.catalogo_egresado'))

    existente = InscripcionesCapacitacion.query.filter_by(
        id_capacitacion=cap.id_capacitacion,
        id_egresado=current_user.id_egresado,
    ).first()
    if existente and existente.estado in ('inscrito', 'asistio'):
        flash('Ya te encuentras inscrito en esta capacitación.', 'info')
        return redirect(url_for('capacitaciones.catalogo_egresado'))

    ocupados = _cupos_ocupados(cap.id_capacitacion)
    if cap.capacidad_maxima and ocupados >= cap.capacidad_maxima:
        flash('Se alcanzó el aforo máximo para esta actividad.', 'warning')
        return redirect(url_for('capacitaciones.catalogo_egresado'))

    if existente:
        existente.estado = 'inscrito'
        existente.fecha_inscripcion = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        db.session.add(InscripcionesCapacitacion(
            id_capacitacion=cap.id_capacitacion,
            id_egresado=current_user.id_egresado,
            estado='inscrito',
        ))
    db.session.commit()

    registrar_auditoria(
        'inscripcion_capacitacion', 'capacitaciones',
        entidad='capacitaciones', id_registro=cap.id_capacitacion,
        detalle=f'Inscripción a "{cap.titulo}"',
    )
    crear_notificacion(
        current_user.id_usuario,
        f'Inscripción confirmada: {cap.titulo}',
        f'Te inscribiste en {TIPOS_DICT.get(cap.tipo, cap.tipo)} ({cap.modalidad}). Fecha de inicio: {cap.fecha_inicio}.',
        tipo='capacitacion',
        enlace='/capacitaciones',
    )
    flash('Inscripción confirmada correctamente.', 'success')
    return redirect(url_for('capacitaciones.catalogo_egresado'))


@capacitaciones.route('/capacitaciones/<int:id_capacitacion>/cancelar', methods=['POST'])
@login_required
def cancelar_inscripcion(id_capacitacion):
    if not current_user.es_egresado():
        abort(403)
    ins = InscripcionesCapacitacion.query.filter_by(
        id_capacitacion=id_capacitacion,
        id_egresado=current_user.id_egresado,
    ).first_or_404()
    if ins.estado != 'inscrito':
        flash('Solo puedes cancelar inscripciones pendientes de asistencia.', 'warning')
        return redirect(url_for('capacitaciones.catalogo_egresado'))
    ins.estado = 'cancelado'
    db.session.commit()
    registrar_auditoria(
        'cancelar_inscripcion', 'capacitaciones',
        entidad='inscripciones_capacitacion', id_registro=ins.id_inscripcion,
    )
    flash('Tu inscripción fue cancelada.', 'info')
    return redirect(url_for('capacitaciones.catalogo_egresado'))


# ============================================================
# ADMIN / UTSAG: GESTIÓN DE CAPACITACIONES Y ASISTENCIA
# ============================================================
@capacitaciones.route('/admin/capacitaciones')
@login_required
@requiere_rol('administrador', 'utsag')
def admin_lista():
    lista = Capacitaciones.query.order_by(Capacitaciones.fecha_inicio.desc()).all()
    stats = {}
    for c in lista:
        inscritos = InscripcionesCapacitacion.query.filter(
            InscripcionesCapacitacion.id_capacitacion == c.id_capacitacion,
            InscripcionesCapacitacion.estado.in_(['inscrito', 'asistio']),
        ).count()
        asistentes = InscripcionesCapacitacion.query.filter_by(
            id_capacitacion=c.id_capacitacion, estado='asistio'
        ).count()
        stats[c.id_capacitacion] = {'inscritos': inscritos, 'asistentes': asistentes}
    return render_template(
        'capacitaciones/admin_lista.html',
        capacitaciones_lista=lista,
        stats=stats,
        tipos=TIPOS_CAPACITACION,
        tipos_dict=TIPOS_DICT,
        modalidades=MODALIDADES_CAP,
        estados=ESTADOS_CAP,
    )


@capacitaciones.route('/admin/capacitaciones/nueva', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def admin_nueva():
    titulo = limpiar_texto(request.form.get('titulo'), 220)
    tipo = limpiar_texto(request.form.get('tipo'), 30) or 'curso'
    modalidad = limpiar_texto(request.form.get('modalidad'), 20) or 'virtual'
    descripcion = limpiar_texto(request.form.get('descripcion'), 2000)
    horario = limpiar_texto(request.form.get('horario'), 120)
    lugar_o_enlace = limpiar_texto(request.form.get('lugar_o_enlace'), 300)
    estado = limpiar_texto(request.form.get('estado'), 20) or 'publicada'

    if not titulo:
        flash('El título de la capacitación es obligatorio.', 'danger')
        return redirect(url_for('capacitaciones.admin_lista'))
    if tipo not in TIPOS_DICT:
        tipo = 'otro'
    if modalidad not in MODALIDADES_CAP:
        modalidad = 'virtual'
    if estado not in ESTADOS_CAP:
        estado = 'publicada'

    try:
        fecha_inicio = parse_fecha_iso(request.form.get('fecha_inicio'), obligatoria=True)
        fecha_fin = parse_fecha_iso(request.form.get('fecha_fin'), obligatoria=False)
        capacidad_maxima = entero_en_rango(request.form.get('capacidad_maxima'), 1, 10000, obligatorio=False)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('capacitaciones.admin_lista'))

    if fecha_fin and fecha_fin < fecha_inicio:
        flash('La fecha de finalización no puede ser anterior a la de inicio.', 'danger')
        return redirect(url_for('capacitaciones.admin_lista'))

    cap = Capacitaciones(
        titulo=titulo,
        tipo=tipo,
        descripcion=descripcion or None,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        horario=horario or None,
        modalidad=modalidad,
        lugar_o_enlace=lugar_o_enlace or None,
        capacidad_maxima=capacidad_maxima,
        estado=estado,
        creado_por=current_user.id_personal,
    )
    db.session.add(cap)
    db.session.commit()
    registrar_auditoria(
        'crear_capacitacion', 'capacitaciones',
        entidad='capacitaciones', id_registro=cap.id_capacitacion,
        detalle=f'Capacitación "{cap.titulo}" ({cap.tipo})',
    )
    flash('Capacitación registrada correctamente.', 'success')
    return redirect(url_for('capacitaciones.admin_lista'))


@capacitaciones.route('/admin/capacitaciones/<int:id_capacitacion>/estado', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def admin_cambiar_estado(id_capacitacion):
    cap = db.session.get(Capacitaciones, id_capacitacion)
    if not cap:
        abort(404)
    nuevo_estado = limpiar_texto(request.form.get('estado'), 20)
    if nuevo_estado not in ESTADOS_CAP:
        flash('Estado no válido.', 'danger')
        return redirect(url_for('capacitaciones.admin_lista'))
    cap.estado = nuevo_estado
    db.session.commit()
    registrar_auditoria(
        'estado_capacitacion', 'capacitaciones',
        entidad='capacitaciones', id_registro=cap.id_capacitacion,
        detalle=f'Nuevo estado: {nuevo_estado}',
    )
    flash(f'Estado actualizado a {nuevo_estado}.', 'success')
    return redirect(url_for('capacitaciones.admin_lista'))


@capacitaciones.route('/admin/capacitaciones/<int:id_capacitacion>/inscritos')
@login_required
@requiere_rol('administrador', 'utsag')
def admin_inscritos(id_capacitacion):
    cap = db.session.get(Capacitaciones, id_capacitacion)
    if not cap:
        abort(404)
    inscritos = (
        InscripcionesCapacitacion.query
        .filter_by(id_capacitacion=cap.id_capacitacion)
        .order_by(InscripcionesCapacitacion.fecha_inscripcion.desc())
        .all()
    )
    return render_template(
        'capacitaciones/admin_inscritos.html',
        cap=cap,
        inscritos=inscritos,
        estados_insc=ESTADOS_INSC,
    )


@capacitaciones.route('/admin/capacitaciones/inscripcion/<int:id_inscripcion>/asistencia', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def admin_marcar_asistencia(id_inscripcion):
    ins = db.session.get(InscripcionesCapacitacion, id_inscripcion)
    if not ins:
        abort(404)
    nuevo_estado = limpiar_texto(request.form.get('estado'), 20)
    if nuevo_estado not in ESTADOS_INSC:
        flash('Estado de asistencia inválido.', 'danger')
        return redirect(url_for('capacitaciones.admin_inscritos', id_capacitacion=ins.id_capacitacion))

    ins.estado = nuevo_estado
    if nuevo_estado == 'asistio' and not ins.codigo_constancia:
        ins.codigo_constancia = f'UNDAC-CAP{ins.id_capacitacion}-{ins.id_inscripcion}-{secrets.token_hex(3).upper()}'
    db.session.commit()

    if nuevo_estado == 'asistio':
        usuario_egr = Usuarios.query.filter_by(id_egresado=ins.id_egresado).first()
        if usuario_egr:
            crear_notificacion(
                usuario_egr.id_usuario,
                f'Constancia emitida: {ins.capacitacion.titulo}',
                f'Se registró tu asistencia. Código de constancia: {ins.codigo_constancia}',
                tipo='capacitacion',
                enlace='/capacitaciones',
            )

    registrar_auditoria(
        'asistencia_capacitacion', 'capacitaciones',
        entidad='inscripciones_capacitacion', id_registro=ins.id_inscripcion,
        detalle=f'Estado asistencia: {nuevo_estado}',
    )
    flash('Asistencia actualizada.', 'success')
    return redirect(url_for('capacitaciones.admin_inscritos', id_capacitacion=ins.id_capacitacion))


# ============================================================
# CENTRO DE NOTIFICACIONES INTERNAS
# ============================================================
@capacitaciones.route('/notificaciones')
@login_required
def mis_notificaciones():
    lista = (
        Notificaciones.query
        .filter_by(id_usuario=current_user.id_usuario)
        .order_by(Notificaciones.creado_en.desc())
        .limit(80)
        .all()
    )
    return render_template('capacitaciones/notificaciones.html', notificaciones=lista)


@capacitaciones.route('/notificaciones/<int:id_notificacion>/leer', methods=['POST'])
@login_required
def leer_notificacion(id_notificacion):
    notif = marcar_como_leida(id_notificacion, current_user.id_usuario)
    if notif and _es_ruta_interna_segura(notif.enlace) and request.form.get('ir') == '1':
        return redirect(notif.enlace)
    return redirect(url_for('capacitaciones.mis_notificaciones'))


@capacitaciones.route('/notificaciones/leer-todas', methods=['POST'])
@login_required
def leer_todas_notificaciones():
    pendientes = Notificaciones.query.filter_by(id_usuario=current_user.id_usuario, leida=0).all()
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    for n in pendientes:
        n.leida = 1
        n.leida_en = ahora
    db.session.commit()
    flash('Todas las notificaciones fueron marcadas como leídas.', 'info')
    return redirect(url_for('capacitaciones.mis_notificaciones'))
