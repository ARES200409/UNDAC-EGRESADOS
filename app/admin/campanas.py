"""Gestión de campañas de seguimiento laboral por períodos y métricas de trayectoria."""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.admin import admin
from app.admin.helpers import requiere_rol, _alcance_programas, _facultades_de_coordinador
from app.extensions import db
from app.models import CampanasSeguimiento, Facultades, ProgramasEstudio, Empleos, Egresados, Curriculas
from app.services.validaciones_service import limpiar_texto, parse_fecha_iso
from app.services.auditoria_service import registrar_auditoria

PERIODOS_SEGUIMIENTO = [
    ('al_egresar', 'Al egresar (cohorte reciente)'),
    ('6_meses', '6 meses después del egreso'),
    ('1_anio', '1 año después del egreso'),
    ('2_anios', '2 años después del egreso'),
    ('3_anios', '3 años después del egreso'),
    ('personalizado', 'Período personalizado'),
]
PERIODOS_DICT = dict(PERIODOS_SEGUIMIENTO)


@admin.route('/admin/campanas')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador')
def campanas():
    rol_activo = current_user.rol_activo_nombre()
    alcance = _alcance_programas(rol_activo, current_user.id_personal)

    q_camp = CampanasSeguimiento.query
    if rol_activo == 'coordinador':
        ids_fac = _facultades_de_coordinador(current_user.id_personal)
        q_camp = q_camp.filter(
            db.or_(
                CampanasSeguimiento.id_facultad.in_(ids_fac) if ids_fac else db.literal(False),
                CampanasSeguimiento.id_programa.in_(alcance) if alcance else db.literal(False),
            )
        )
    lista = q_camp.order_by(CampanasSeguimiento.creado_en.desc()).all()

    # Métricas reales de seguimiento laboral en el ámbito
    q_emp = (
        Empleos.query
        .join(Egresados, Empleos.id_egresado == Egresados.id_egresado)
        .join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)
    )
    if alcance is not None:
        q_emp = q_emp.filter(Curriculas.id_programa.in_(alcance)) if alcance else q_emp.filter(db.literal(False))

    empleos_totales = q_emp.count()
    relacionados = q_emp.filter(Empleos.relacion_carrera == 1).count()
    independientes = q_emp.filter(Empleos.es_independiente == 1).count()

    facultades = Facultades.query.order_by(Facultades.nombre).all()
    if rol_activo == 'coordinador':
        ids_fac = _facultades_de_coordinador(current_user.id_personal)
        facultades = [f for f in facultades if f.id_facultad in ids_fac]

    programas = ProgramasEstudio.query.order_by(ProgramasEstudio.nombre).all()
    if alcance is not None:
        programas = [p for p in programas if p.id_programa in alcance]

    return render_template(
        'admin/campanas.html',
        campanas=lista,
        periodos=PERIODOS_SEGUIMIENTO,
        periodos_dict=PERIODOS_DICT,
        facultades=facultades,
        programas=programas,
        metricas={
            'empleos': empleos_totales,
            'relacionados': relacionados,
            'independientes': independientes,
        },
    )


@admin.route('/admin/campanas/nueva', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador')
def nueva_campana():
    nombre = limpiar_texto(request.form.get('nombre'), 200)
    descripcion = limpiar_texto(request.form.get('descripcion'), 500) or None
    periodo_tipo = request.form.get('periodo_tipo', '1_anio').strip()
    id_facultad = request.form.get('id_facultad', type=int) or None
    id_programa = request.form.get('id_programa', type=int) or None

    if not nombre:
        flash('El nombre de la campaña es obligatorio.', 'warning')
        return redirect(url_for('admin.campanas'))
    if periodo_tipo not in PERIODOS_DICT:
        periodo_tipo = 'personalizado'

    try:
        fecha_inicio = parse_fecha_iso(request.form.get('fecha_inicio'), obligatoria=False)
        fecha_fin = parse_fecha_iso(request.form.get('fecha_fin'), obligatoria=False)
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValueError('La fecha de cierre no puede ser anterior al inicio.')
    except ValueError as exc:
        flash(str(exc), 'warning')
        return redirect(url_for('admin.campanas'))

    rol_activo = current_user.rol_activo_nombre()
    if rol_activo == 'coordinador':
        ids_fac = _facultades_de_coordinador(current_user.id_personal)
        alcance = _alcance_programas(rol_activo, current_user.id_personal)
        if id_facultad and id_facultad not in ids_fac:
            flash('Facultad fuera de tu ámbito autorizado.', 'danger')
            return redirect(url_for('admin.campanas'))
        if id_programa and id_programa not in alcance:
            flash('Programa fuera de tu ámbito autorizado.', 'danger')
            return redirect(url_for('admin.campanas'))

    camp = CampanasSeguimiento(
        nombre=nombre,
        descripcion=descripcion,
        periodo_tipo=periodo_tipo,
        id_facultad=id_facultad,
        id_programa=id_programa,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado='activa' if request.form.get('activar') == '1' else 'borrador',
        creado_por=current_user.id_personal,
    )
    db.session.add(camp)
    db.session.commit()
    registrar_auditoria('crear_campana', 'seguimiento', 'campanas_seguimiento', camp.id_campana)
    flash(f'Campaña "{camp.nombre}" registrada correctamente.', 'success')
    return redirect(url_for('admin.campanas'))


@admin.route('/admin/campanas/<int:id_campana>/estado', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador')
def cambiar_estado_campana(id_campana):
    camp = CampanasSeguimiento.query.get_or_404(id_campana)
    nuevo = request.form.get('estado', '').strip()
    if nuevo not in ('borrador', 'activa', 'cerrada'):
        flash('Estado no válido.', 'warning')
        return redirect(url_for('admin.campanas'))
    camp.estado = nuevo
    db.session.commit()
    registrar_auditoria('cambiar_estado_campana', 'seguimiento', 'campanas_seguimiento', camp.id_campana, detalle=nuevo)
    flash(f'Campaña actualizada a "{nuevo}".', 'success')
    return redirect(url_for('admin.campanas'))
