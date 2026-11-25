"""Reportes consolidados institucionales con filtros por rango de fechas y facultad."""

import io
from datetime import datetime, time
from flask import render_template, request, send_file, abort, flash
from flask_login import login_required, current_user
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.admin import admin
from app.admin.helpers import requiere_rol, _alcance_programas, _facultades_de_coordinador
from app.extensions import db
from app.models import (
    Egresados, Curriculas, ProgramasEstudio, Facultades, Empleos, Usuarios,
    DocumentosEgresado, Capacitaciones, InscripcionesCapacitacion,
    CampanasSeguimiento, OfertasLaborales, Postulaciones,
)
from app.services.validaciones_service import parse_fecha_iso


def _validar_alcance_filtros(rol_activo, id_personal, id_facultad, id_programa):
    alcance = _alcance_programas(rol_activo, id_personal)
    if alcance is not None:
        if id_programa and id_programa not in alcance:
            abort(403)
        if id_facultad:
            if rol_activo == 'coordinador' and id_facultad not in _facultades_de_coordinador(id_personal):
                abort(403)
            if rol_activo == 'docente_responsable':
                id_facultad = None
    return alcance, id_facultad, id_programa


def construir_resumen_consolidado(rol_activo, id_personal, id_facultad=None, id_programa=None, fecha_desde=None, fecha_hasta=None):
    """Agrega KPIs de padrón, empleabilidad, documentos, capacitaciones, campañas y bolsa laboral."""
    alcance, id_facultad, id_programa = _validar_alcance_filtros(rol_activo, id_personal, id_facultad, id_programa)

    q_egr = Egresados.query.join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)
    if alcance is not None:
        q_egr = q_egr.filter(Curriculas.id_programa.in_(alcance)) if alcance else q_egr.filter(db.literal(False))
    if id_programa:
        q_egr = q_egr.filter(Curriculas.id_programa == id_programa)
    elif id_facultad:
        q_egr = q_egr.join(ProgramasEstudio, Curriculas.id_programa == ProgramasEstudio.id_programa)\
                     .filter(ProgramasEstudio.id_facultad == id_facultad)

    subq_egr = q_egr.with_entities(Egresados.id_egresado).scalar_subquery()

    total_egresados = q_egr.count()
    con_cuenta = q_egr.join(Usuarios, Usuarios.id_egresado == Egresados.id_egresado).distinct().count()

    q_emp = Empleos.query.filter(Empleos.id_egresado.in_(subq_egr))
    if fecha_desde:
        q_emp = q_emp.filter(Empleos.fecha_inicio >= fecha_desde)
    if fecha_hasta:
        q_emp = q_emp.filter(Empleos.fecha_inicio <= fecha_hasta)
    empleos_total = q_emp.count()
    empleos_actuales = q_emp.filter(Empleos.es_actual == 1).count()
    empleos_relacion = q_emp.filter(Empleos.relacion_carrera == 1).count()

    q_docs = DocumentosEgresado.query.filter(DocumentosEgresado.id_egresado.in_(subq_egr))
    if fecha_desde:
        q_docs = q_docs.filter(DocumentosEgresado.creado_en >= datetime.combine(fecha_desde, time.min))
    if fecha_hasta:
        q_docs = q_docs.filter(DocumentosEgresado.creado_en <= datetime.combine(fecha_hasta, time.max))
    docs_total = q_docs.count()
    docs_validados = q_docs.filter(DocumentosEgresado.estado_validacion == 'validado').count()
    docs_pendientes = q_docs.filter(DocumentosEgresado.estado_validacion.in_(['pendiente', 'en_revision'])).count()
    docs_observados = q_docs.filter(DocumentosEgresado.estado_validacion.in_(['observado', 'rechazado'])).count()

    q_cap = Capacitaciones.query
    if fecha_desde:
        q_cap = q_cap.filter(Capacitaciones.fecha_inicio >= fecha_desde)
    if fecha_hasta:
        q_cap = q_cap.filter(Capacitaciones.fecha_inicio <= fecha_hasta)
    cap_total = q_cap.count()
    cap_publicadas = q_cap.filter(Capacitaciones.estado == 'publicada').count()

    q_insc = InscripcionesCapacitacion.query.filter(InscripcionesCapacitacion.id_egresado.in_(subq_egr))
    if fecha_desde:
        q_insc = q_insc.filter(InscripcionesCapacitacion.fecha_inscripcion >= datetime.combine(fecha_desde, time.min))
    if fecha_hasta:
        q_insc = q_insc.filter(InscripcionesCapacitacion.fecha_inscripcion <= datetime.combine(fecha_hasta, time.max))
    cap_inscripciones = q_insc.filter(InscripcionesCapacitacion.estado.in_(['inscrito', 'asistio'])).count()
    cap_asistencias = q_insc.filter(InscripcionesCapacitacion.estado == 'asistio').count()

    q_camp = CampanasSeguimiento.query
    if fecha_desde:
        q_camp = q_camp.filter(db.or_(CampanasSeguimiento.fecha_inicio.is_(None), CampanasSeguimiento.fecha_inicio >= fecha_desde))
    if fecha_hasta:
        q_camp = q_camp.filter(db.or_(CampanasSeguimiento.fecha_inicio.is_(None), CampanasSeguimiento.fecha_inicio <= fecha_hasta))
    camp_total = q_camp.count()
    camp_activas = q_camp.filter(CampanasSeguimiento.estado == 'activa').count()

    ofertas_activas = OfertasLaborales.query.filter_by(activa=1).count()
    postulaciones_total = Postulaciones.query.filter(Postulaciones.id_egresado.in_(subq_egr)).count()

    return {
        'total_egresados': total_egresados,
        'con_cuenta': con_cuenta,
        'empleos_total': empleos_total,
        'empleos_actuales': empleos_actuales,
        'empleos_relacion': empleos_relacion,
        'docs_total': docs_total,
        'docs_validados': docs_validados,
        'docs_pendientes': docs_pendientes,
        'docs_observados': docs_observados,
        'cap_total': cap_total,
        'cap_publicadas': cap_publicadas,
        'cap_inscripciones': cap_inscripciones,
        'cap_asistencias': cap_asistencias,
        'camp_total': camp_total,
        'camp_activas': camp_activas,
        'ofertas_activas': ofertas_activas,
        'postulaciones_total': postulaciones_total,
        'q_egr': q_egr,
        'q_docs': q_docs,
        'q_cap': q_cap,
    }


def _leer_filtros_request():
    id_facultad = request.args.get('id_facultad', type=int)
    id_programa = request.args.get('id_programa', type=int)
    fecha_desde = None
    fecha_hasta = None
    try:
        fecha_desde = parse_fecha_iso(request.args.get('fecha_desde'), obligatoria=False)
        fecha_hasta = parse_fecha_iso(request.args.get('fecha_hasta'), obligatoria=False)
    except ValueError as exc:
        flash(str(exc), 'warning')
    if fecha_desde and fecha_hasta and fecha_hasta < fecha_desde:
        flash('La fecha final no puede ser anterior a la fecha inicial.', 'warning')
        fecha_desde, fecha_hasta = None, None
    return id_facultad, id_programa, fecha_desde, fecha_hasta


@admin.route('/admin/reportes')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador')
def reportes_consolidados():
    rol_activo = current_user.rol_activo_nombre()
    id_facultad, id_programa, fecha_desde, fecha_hasta = _leer_filtros_request()
    resumen = construir_resumen_consolidado(
        rol_activo, current_user.id_personal, id_facultad, id_programa, fecha_desde, fecha_hasta
    )

    facultades = Facultades.query.order_by(Facultades.nombre).all()
    if rol_activo == 'coordinador':
        ids_fac = _facultades_de_coordinador(current_user.id_personal)
        facultades = [f for f in facultades if f.id_facultad in ids_fac]

    return render_template(
        'admin/reportes_consolidados.html',
        resumen=resumen,
        facultades=facultades,
        id_facultad=id_facultad,
        fecha_desde=fecha_desde.isoformat() if fecha_desde else '',
        fecha_hasta=fecha_hasta.isoformat() if fecha_hasta else '',
    )


@admin.route('/admin/reportes/excel')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador')
def reporte_consolidado_excel():
    rol_activo = current_user.rol_activo_nombre()
    id_facultad, id_programa, fecha_desde, fecha_hasta = _leer_filtros_request()
    r = construir_resumen_consolidado(
        rol_activo, current_user.id_personal, id_facultad, id_programa, fecha_desde, fecha_hasta
    )

    wb = Workbook()
    ws_res = wb.active
    ws_res.title = 'Resumen KPIs'
    ws_res.append(['Indicador', 'Valor'])
    for etiqueta, clave in [
        ('Total egresados en ámbito', 'total_egresados'),
        ('Egresados con cuenta activa', 'con_cuenta'),
        ('Registros de empleo', 'empleos_total'),
        ('Empleos actuales', 'empleos_actuales'),
        ('Empleos relacionados a carrera', 'empleos_relacion'),
        ('Documentos digitales totales', 'docs_total'),
        ('Documentos validados', 'docs_validados'),
        ('Documentos pendientes', 'docs_pendientes'),
        ('Documentos observados/rechazados', 'docs_observados'),
        ('Capacitaciones registradas', 'cap_total'),
        ('Capacitaciones publicadas', 'cap_publicadas'),
        ('Inscripciones activas', 'cap_inscripciones'),
        ('Asistencias confirmadas', 'cap_asistencias'),
        ('Campañas de seguimiento', 'camp_total'),
        ('Campañas activas', 'camp_activas'),
        ('Ofertas laborales activas', 'ofertas_activas'),
        ('Postulaciones registradas', 'postulaciones_total'),
    ]:
        ws_res.append([etiqueta, r[clave]])

    ws_egr = wb.create_sheet('Egresados')
    ws_egr.append(['DNI', 'Apellidos y Nombres', 'Año Egreso', 'Nivel Máximo', 'Situación Laboral'])
    for e in r['q_egr'].order_by(Egresados.apellido_paterno).limit(2000).all():
        ws_egr.append([e.dni, e.nombre_completo(), e.anio_egreso or '', e.nivel_maximo or '', e.situacion_laboral or ''])

    ws_doc = wb.create_sheet('Documentos')
    ws_doc.append(['ID', 'Documento', 'Categoría', 'Estado Validación', 'Fecha Carga'])
    for d in r['q_docs'].order_by(DocumentosEgresado.creado_en.desc()).limit(2000).all():
        ws_doc.append([d.id_documento, d.nombre, d.categoria, d.estado_validacion, d.creado_en.strftime('%Y-%m-%d') if d.creado_en else ''])

    ws_cap = wb.create_sheet('Capacitaciones')
    ws_cap.append(['ID', 'Título', 'Tipo', 'Modalidad', 'Fecha Inicio', 'Estado'])
    for c in r['q_cap'].order_by(Capacitaciones.fecha_inicio.desc()).limit(1000).all():
        ws_cap.append([c.id_capacitacion, c.titulo, c.tipo, c.modalidad, str(c.fecha_inicio), c.estado])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='reporte_consolidado_nexo_undac.xlsx',
    )


@admin.route('/admin/reportes/pdf')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador')
def reporte_consolidado_pdf():
    rol_activo = current_user.rol_activo_nombre()
    id_facultad, id_programa, fecha_desde, fecha_hasta = _leer_filtros_request()
    r = construir_resumen_consolidado(
        rol_activo, current_user.id_personal, id_facultad, id_programa, fecha_desde, fecha_hasta
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elementos = [
        Paragraph('NEXO UNDAC — Reporte Institucional Consolidado', styles['Title']),
        Paragraph(
            f'Generado por: {current_user.correo} · Rol: {rol_activo} · Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
            styles['Normal'],
        ),
        Spacer(1, 12),
    ]

    filas = [
        ['Módulo / Indicador', 'Cantidad'],
        ['Egresados en padrón', str(r['total_egresados'])],
        ['Egresados con cuenta activa', str(r['con_cuenta'])],
        ['Empleos registrados / actuales', f"{r['empleos_total']} / {r['empleos_actuales']}"],
        ['Empleos relacionados a carrera', str(r['empleos_relacion'])],
        ['Documentos totales / validados / pendientes', f"{r['docs_total']} / {r['docs_validados']} / {r['docs_pendientes']}"],
        ['Capacitaciones / Inscripciones / Asistencias', f"{r['cap_total']} / {r['cap_inscripciones']} / {r['cap_asistencias']}"],
        ['Campañas totales / activas', f"{r['camp_total']} / {r['camp_activas']}"],
        ['Ofertas activas / Postulaciones', f"{r['ofertas_activas']} / {r['postulaciones_total']}"],
    ]
    tabla = Table(filas, colWidths=[340, 140])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#152631')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='reporte_consolidado_nexo_undac.pdf',
    )
