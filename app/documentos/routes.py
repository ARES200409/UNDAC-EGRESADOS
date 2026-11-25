"""Rutas de gestión documental privada, certificaciones y validación administrativa."""

import os
from datetime import datetime, timezone
from flask import (
    render_template, request, redirect, url_for, flash,
    send_file, abort
)
from flask_login import login_required, current_user

from app.documentos import documentos
from app.extensions import db
from app.models import (
    DocumentosEgresado, HistorialValidacionDocumental, AutorizacionesDocumentales,
    Egresados, Curriculas, ProgramasEstudio, Facultades, Usuarios
)
from app.egresado.routes import solo_egresado
from app.admin.helpers import requiere_rol, _alcance_programas, _facultades_de_coordinador
from app.services.almacenamiento_service import (
    guardar_documento_privado, resolver_ruta_privada, eliminar_documento_privado
)
from app.services.auditoria_service import registrar_auditoria
from app.services.notificaciones_service import crear_notificacion
from app.services.validaciones_service import limpiar_texto, parse_fecha_iso


CATEGORIAS_DOCUMENTO = [
    ('cv', 'Currículum Vitae (CV)'),
    ('certificado_estudios', 'Certificado de estudios'),
    ('capacitacion', 'Certificado de capacitación'),
    ('curso', 'Certificado de curso'),
    ('especializacion', 'Certificado de especialización'),
    ('idioma', 'Certificado de idioma'),
    ('constancia_trabajo', 'Constancia de trabajo'),
    ('certificado_laboral', 'Certificado laboral'),
    ('diploma', 'Diploma'),
    ('grado_academico', 'Grado académico'),
    ('titulo_profesional', 'Título profesional'),
    ('reconocimiento', 'Reconocimiento'),
    ('practicas', 'Constancia de prácticas'),
    ('otro', 'Otro documento'),
]
CATEGORIAS_DICT = dict(CATEGORIAS_DOCUMENTO)

ESTADOS_DOCUMENTO = {
    'pendiente': 'Pendiente de revisión',
    'en_revision': 'En revisión',
    'validado': 'Validado',
    'observado': 'Observado',
    'rechazado': 'Rechazado',
}


def _usuario_puede_ver_documento(doc, usuario):
    """Control de acceso en servidor para visualización y descarga documental."""
    if not usuario or not usuario.is_authenticated:
        return False

    # 1. Propietario egresado
    if usuario.es_egresado():
        return doc.id_egresado == usuario.id_egresado

    # 2. Empresa: únicamente si existe autorización expresa y vigente
    if usuario.es_empresa():
        if not usuario.id_empresa:
            return False
        aut = AutorizacionesDocumentales.query.filter_by(
            id_documento=doc.id_documento,
            id_empresa=usuario.id_empresa,
            autorizado=1,
            revocado_en=None,
        ).first()
        return aut is not None

    # 3. Personal institucional dentro de su ámbito académico
    rol_activo = usuario.rol_activo_nombre()
    if rol_activo in ('administrador', 'utsag', 'coordinador', 'docente_responsable'):
        alcance = _alcance_programas(rol_activo, usuario.id_personal)
        if alcance is None:
            return True
        eg = doc.egresado
        return bool(eg and eg.curricula and eg.curricula.id_programa in alcance)

    return False


# ============================================================
# PANEL DOCUMENTAL DEL EGRESADO
# ============================================================

@documentos.route('/documentos')
@login_required
@solo_egresado
def mis_documentos():
    categoria = request.args.get('categoria', '').strip()
    estado = request.args.get('estado', '').strip()
    buscar = request.args.get('buscar', '').strip()[:100]

    q = DocumentosEgresado.query.filter_by(id_egresado=current_user.id_egresado)
    if categoria and categoria in CATEGORIAS_DICT:
        q = q.filter_by(categoria=categoria)
    if estado and estado in ESTADOS_DOCUMENTO:
        q = q.filter_by(estado_validacion=estado)
    if buscar:
        like = f'%{buscar}%'
        q = q.filter(db.or_(
            DocumentosEgresado.nombre.ilike(like),
            DocumentosEgresado.institucion_emisora.ilike(like),
            DocumentosEgresado.nombre_original.ilike(like),
        ))

    lista = q.order_by(DocumentosEgresado.creado_en.desc()).all()
    todos = DocumentosEgresado.query.filter_by(id_egresado=current_user.id_egresado).all()

    resumen = {
        'total': len(todos),
        'validados': sum(1 for d in todos if d.estado_validacion == 'validado'),
        'pendientes': sum(1 for d in todos if d.estado_validacion in ('pendiente', 'en_revision')),
        'observados': sum(1 for d in todos if d.estado_validacion in ('observado', 'rechazado')),
    }
    return render_template(
        'documentos/mis_documentos.html',
        docs=lista,
        resumen=resumen,
        categorias=CATEGORIAS_DOCUMENTO,
        categorias_dict=CATEGORIAS_DICT,
        estados=ESTADOS_DOCUMENTO,
        filtro_categoria=categoria,
        filtro_estado=estado,
        buscar=buscar,
    )


@documentos.route('/documentos/subir', methods=['POST'])
@login_required
@solo_egresado
def subir_documento():
    nombre = limpiar_texto(request.form.get('nombre'), 200)
    categoria = limpiar_texto(request.form.get('categoria'), 40) or 'otro'
    descripcion = limpiar_texto(request.form.get('descripcion'), 500) or None
    institucion = limpiar_texto(request.form.get('institucion_emisora'), 200) or None

    if not nombre:
        flash('Indica un nombre descriptivo para el documento.', 'warning')
        return redirect(url_for('documentos.mis_documentos'))
    if categoria not in CATEGORIAS_DICT:
        categoria = 'otro'

    try:
        fecha_emision = parse_fecha_iso(request.form.get('fecha_emision'), obligatoria=False)
        fecha_vencimiento = parse_fecha_iso(request.form.get('fecha_vencimiento'), obligatoria=False)
    except ValueError as exc:
        flash(str(exc), 'warning')
        return redirect(url_for('documentos.mis_documentos'))

    archivo = request.files.get('archivo')
    try:
        guardado = guardar_documento_privado(archivo, subcarpeta=f'egresado_{current_user.id_egresado}')
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('documentos.mis_documentos'))

    es_cv_principal = 1 if (categoria == 'cv' and request.form.get('es_cv_principal') == '1') else 0
    if es_cv_principal:
        DocumentosEgresado.query.filter_by(
            id_egresado=current_user.id_egresado, es_cv_principal=1
        ).update({'es_cv_principal': 0})

    doc = DocumentosEgresado(
        id_egresado=current_user.id_egresado,
        nombre=nombre,
        categoria=categoria,
        descripcion=descripcion,
        institucion_emisora=institucion,
        fecha_emision=fecha_emision,
        fecha_vencimiento=fecha_vencimiento,
        nombre_original=guardado.nombre_original,
        nombre_interno=guardado.nombre_interno,
        ruta_almacenamiento=guardado.ruta_relativa,
        extension=guardado.extension,
        mime_type=guardado.mime_type,
        tamano_bytes=guardado.tamano_bytes,
        sha256=guardado.sha256,
        es_cv_principal=es_cv_principal,
        estado_validacion='pendiente',
    )
    db.session.add(doc)
    db.session.commit()

    registrar_auditoria(
        'subir_documento', 'documentos', 'documentos_egresado', doc.id_documento,
        detalle=f'Categoría: {categoria}, ext: {guardado.extension}'
    )
    flash('Documento cargado de forma privada y segura. Quedó pendiente de validación.', 'success')
    return redirect(url_for('documentos.mis_documentos'))


@documentos.route('/documentos/<int:id_doc>/reemplazar', methods=['POST'])
@login_required
@solo_egresado
def reemplazar_documento(id_doc):
    doc = DocumentosEgresado.query.get_or_404(id_doc)
    if doc.id_egresado != current_user.id_egresado:
        registrar_auditoria('reemplazo_denegado', 'documentos', 'documentos_egresado', id_doc, resultado='denegado')
        abort(403)

    archivo = request.files.get('archivo')
    try:
        nuevo = guardar_documento_privado(archivo, subcarpeta=f'egresado_{current_user.id_egresado}')
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('documentos.mis_documentos'))

    ruta_anterior = doc.ruta_almacenamiento
    estado_anterior = doc.estado_validacion

    doc.nombre_original = nuevo.nombre_original
    doc.nombre_interno = nuevo.nombre_interno
    doc.ruta_almacenamiento = nuevo.ruta_relativa
    doc.extension = nuevo.extension
    doc.mime_type = nuevo.mime_type
    doc.tamano_bytes = nuevo.tamano_bytes
    doc.sha256 = nuevo.sha256
    doc.estado_validacion = 'pendiente'
    doc.observaciones = None

    db.session.add(HistorialValidacionDocumental(
        id_documento=doc.id_documento,
        estado_anterior=estado_anterior,
        estado_nuevo='pendiente',
        observacion='Archivo reemplazado por el egresado',
    ))
    db.session.commit()
    eliminar_documento_privado(ruta_anterior)

    registrar_auditoria('reemplazar_documento', 'documentos', 'documentos_egresado', doc.id_documento)
    flash('Documento reemplazado correctamente y enviado a nueva revisión.', 'success')
    return redirect(url_for('documentos.mis_documentos'))


@documentos.route('/documentos/<int:id_doc>/cv-principal', methods=['POST'])
@login_required
@solo_egresado
def marcar_cv_principal(id_doc):
    doc = DocumentosEgresado.query.get_or_404(id_doc)
    if doc.id_egresado != current_user.id_egresado:
        abort(403)
    if doc.categoria != 'cv':
        flash('Solo los documentos de categoría Currículum Vitae pueden marcarse como CV principal.', 'warning')
        return redirect(url_for('documentos.mis_documentos'))

    DocumentosEgresado.query.filter_by(
        id_egresado=current_user.id_egresado, es_cv_principal=1
    ).update({'es_cv_principal': 0})
    doc.es_cv_principal = 1
    db.session.commit()
    flash('CV marcado como versión principal para postulaciones.', 'success')
    return redirect(url_for('documentos.mis_documentos'))


@documentos.route('/documentos/<int:id_doc>/eliminar', methods=['POST'])
@login_required
@solo_egresado
def eliminar_documento(id_doc):
    doc = DocumentosEgresado.query.get_or_404(id_doc)
    if doc.id_egresado != current_user.id_egresado:
        registrar_auditoria('eliminar_documento_denegado', 'documentos', 'documentos_egresado', id_doc, resultado='denegado')
        abort(403)
    if doc.estado_validacion == 'validado':
        flash('Un documento ya validado institucionalmente no puede eliminarse directamente.', 'warning')
        return redirect(url_for('documentos.mis_documentos'))

    ruta = doc.ruta_almacenamiento
    db.session.delete(doc)
    db.session.commit()
    eliminar_documento_privado(ruta)

    registrar_auditoria('eliminar_documento', 'documentos', 'documentos_egresado', id_doc)
    flash('Documento eliminado.', 'info')
    return redirect(url_for('documentos.mis_documentos'))


# ============================================================
# RUTA PROTEGIDA DE DESCARGA / VISTA PREVIA
# ============================================================

@documentos.route('/documentos/<int:id_doc>/archivo')
@login_required
def descargar_documento(id_doc):
    doc = DocumentosEgresado.query.get_or_404(id_doc)
    if not _usuario_puede_ver_documento(doc, current_user):
        registrar_auditoria(
            'descarga_documento_denegada', 'documentos', 'documentos_egresado',
            id_doc, resultado='denegado'
        )
        abort(403)

    ruta_abs = resolver_ruta_privada(doc.ruta_almacenamiento)
    if not ruta_abs or not os.path.isfile(ruta_abs):
        abort(404)

    vista_previa = request.args.get('ver') == '1'
    registrar_auditoria(
        'ver_documento' if vista_previa else 'descargar_documento',
        'documentos', 'documentos_egresado', id_doc
    )
    return send_file(
        ruta_abs,
        mimetype=doc.mime_type,
        as_attachment=not vista_previa,
        download_name=doc.nombre_original,
    )


# ============================================================
# GESTIÓN Y VALIDACIÓN DOCUMENTAL ADMINISTRATIVA
# ============================================================

@documentos.route('/admin/documentos')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def admin_documentos():
    rol_activo = current_user.rol_activo_nombre()
    alcance = _alcance_programas(rol_activo, current_user.id_personal)

    estado = request.args.get('estado', '').strip()
    categoria = request.args.get('categoria', '').strip()
    id_facultad = request.args.get('id_facultad', type=int)
    id_programa = request.args.get('id_programa', type=int)
    buscar = request.args.get('buscar', '').strip()[:100]

    q = (
        DocumentosEgresado.query
        .join(Egresados, DocumentosEgresado.id_egresado == Egresados.id_egresado)
        .join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)
        .join(ProgramasEstudio, Curriculas.id_programa == ProgramasEstudio.id_programa)
    )
    if alcance is not None:
        q = q.filter(Curriculas.id_programa.in_(alcance)) if alcance else q.filter(db.literal(False))
    if id_programa:
        q = q.filter(ProgramasEstudio.id_programa == id_programa)
    elif id_facultad:
        q = q.filter(ProgramasEstudio.id_facultad == id_facultad)
    if estado and estado in ESTADOS_DOCUMENTO:
        q = q.filter(DocumentosEgresado.estado_validacion == estado)
    if categoria and categoria in CATEGORIAS_DICT:
        q = q.filter(DocumentosEgresado.categoria == categoria)
    if buscar:
        like = f'%{buscar}%'
        q = q.filter(db.or_(
            DocumentosEgresado.nombre.ilike(like),
            Egresados.nombres.ilike(like),
            Egresados.apellido_paterno.ilike(like),
            Egresados.dni.ilike(like),
        ))

    lista = q.order_by(DocumentosEgresado.creado_en.desc()).limit(150).all()

    facultades = Facultades.query.order_by(Facultades.nombre).all()
    if rol_activo == 'coordinador':
        ids_fac = _facultades_de_coordinador(current_user.id_personal)
        facultades = [f for f in facultades if f.id_facultad in ids_fac]

    programas = ProgramasEstudio.query.order_by(ProgramasEstudio.nombre).all()
    if alcance is not None:
        programas = [p for p in programas if p.id_programa in alcance]

    return render_template(
        'documentos/admin_documentos.html',
        docs=lista,
        categorias=CATEGORIAS_DOCUMENTO,
        categorias_dict=CATEGORIAS_DICT,
        estados=ESTADOS_DOCUMENTO,
        facultades=facultades,
        programas=programas,
        filtros={
            'estado': estado, 'categoria': categoria,
            'id_facultad': id_facultad, 'id_programa': id_programa, 'buscar': buscar
        },
    )


@documentos.route('/admin/documentos/<int:id_doc>/revisar', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador')
def revisar_documento(id_doc):
    doc = DocumentosEgresado.query.get_or_404(id_doc)
    if not _usuario_puede_ver_documento(doc, current_user):
        abort(403)

    nuevo_estado = request.form.get('estado_validacion', '').strip()
    observacion = limpiar_texto(request.form.get('observaciones'), 500)

    if nuevo_estado not in ('en_revision', 'validado', 'observado', 'rechazado'):
        flash('Estado de validación inválido.', 'warning')
        return redirect(url_for('documentos.admin_documentos'))

    if nuevo_estado in ('observado', 'rechazado') and not observacion:
        flash('Debes indicar el motivo u observación al observar o rechazar un documento.', 'warning')
        return redirect(url_for('documentos.admin_documentos'))

    estado_anterior = doc.estado_validacion
    doc.estado_validacion = nuevo_estado
    doc.observaciones = observacion or None
    doc.revisado_por = current_user.id_personal
    doc.fecha_revision = datetime.now(timezone.utc).replace(tzinfo=None)

    db.session.add(HistorialValidacionDocumental(
        id_documento=doc.id_documento,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        observacion=observacion or None,
        id_personal=current_user.id_personal,
    ))
    db.session.commit()

    registrar_auditoria(
        'revisar_documento', 'documentos', 'documentos_egresado', doc.id_documento,
        detalle=f'{estado_anterior} -> {nuevo_estado}'
    )

    # Notificar al egresado sobre el resultado de la revisión
    usuario_egr = Usuarios.query.filter_by(id_egresado=doc.id_egresado).first()
    if usuario_egr:
        etiqueta = ESTADOS_DOCUMENTO.get(nuevo_estado, nuevo_estado)
        msg = f'Tu documento "{doc.nombre}" pasó a estado: {etiqueta}.'
        if observacion:
            msg += f' Observación: {observacion}'
        crear_notificacion(
            usuario_egr.id_usuario,
            titulo=f'Actualización documental: {etiqueta}',
            mensaje=msg,
            tipo='documento',
            enlace=url_for('documentos.mis_documentos'),
        )

    flash(f'Documento actualizado a "{ESTADOS_DOCUMENTO.get(nuevo_estado)}".', 'success')
    return redirect(url_for('documentos.admin_documentos'))
