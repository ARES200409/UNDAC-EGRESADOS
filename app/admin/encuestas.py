# app/admin/encuestas.py
from flask import render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from app.admin import admin
from app.admin.helpers import (requiere_rol, _alcance_programas, _facultades_de_coordinador, _query_respuestas_filtradas)
from app.extensions import db
from app.models import Encuesta, Preguntas, Opciones, Respuestas, ProgramasEstudio, Facultades
from datetime import date


@admin.route('/admin/encuestas')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def encuestas():
    rol_activo = current_user.rol_activo_nombre()
    q = Encuesta.query
    if rol_activo not in ('administrador', 'utsag'):
        q = q.filter(Encuesta.estado != 'borrador')
    lista = q.order_by(Encuesta.anio.desc(), Encuesta.id_encuesta.desc()).all()
    return render_template('admin/encuestas.html', encuestas=lista, rol_activo=rol_activo)


@admin.route('/admin/encuestas/nueva', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def nueva_encuesta():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        try:
            anio = int(request.form.get('anio', ''))
        except (TypeError, ValueError):
            anio = None
        inicio = request.form.get('fecha_inicio') or None
        fin = request.form.get('fecha_fin') or None
        if not nombre or len(nombre) > 200 or anio is None or anio < 2000 or anio > 2100:
            flash('Indica un nombre y un año válido para la encuesta.', 'warning')
            return render_template('admin/nueva_encuesta.html', anio_actual=date.today().year), 400
        try:
            if inicio:
                date.fromisoformat(inicio)
            if fin:
                date.fromisoformat(fin)
            if inicio and fin and inicio > fin:
                raise ValueError('El inicio es posterior al fin')
        except ValueError:
            flash('Las fechas de la encuesta son inválidas o están invertidas.', 'warning')
            return render_template('admin/nueva_encuesta.html', anio_actual=date.today().year), 400
        enc = Encuesta(
            nombre       = nombre,
            descripcion  = request.form.get('descripcion', '').strip() or None,
            anio         = anio,
            fecha_inicio = inicio,
            fecha_fin    = fin,
            estado       = 'borrador'
        )
        db.session.add(enc)
        db.session.commit()
        flash('Encuesta creada. Ahora agrega las preguntas.', 'success')
        return redirect(url_for('admin.detalle_encuesta', id=enc.id_encuesta))

    return render_template('admin/nueva_encuesta.html', anio_actual=date.today().year)


@admin.route('/admin/encuestas/<int:id>')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def detalle_encuesta(id):
    enc = Encuesta.query.get_or_404(id)
    rol_activo = current_user.rol_activo_nombre()

    if enc.estado == 'borrador' and rol_activo not in ('administrador', 'utsag'):
        flash('Esta encuesta aún no está disponible.', 'warning')
        return redirect(url_for('admin.encuestas'))

    preguntas = Preguntas.query.filter_by(id_encuesta=id).order_by(Preguntas.orden).all()
    alcance = _alcance_programas(rol_activo, current_user.id_personal)
    total_respuestas = _query_respuestas_filtradas(
        id, ids_programas_forzado=alcance).with_entities(Respuestas.id_egresado).distinct().count()
    return render_template('admin/detalle_encuesta.html',
        encuesta=enc, preguntas=preguntas, total_respuestas=total_respuestas, rol_activo=rol_activo)


@admin.route('/admin/encuestas/<int:id>/preguntas/nueva', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def nueva_pregunta(id):
    Encuesta.query.get_or_404(id)

    tipo  = request.form.get('tipo', '').strip()
    texto = request.form.get('texto', '').strip()

    if not texto or tipo not in ('texto', 'numero', 'si_no', 'opcion_unica', 'opcion_multiple'):
        flash('Datos de la pregunta inválidos.', 'danger')
        return redirect(url_for('admin.detalle_encuesta', id=id))

    max_orden = db.session.query(db.func.max(Preguntas.orden)).filter_by(id_encuesta=id).scalar() or 0

    pregunta = Preguntas(
        id_encuesta = id,
        texto       = texto,
        tipo        = tipo,
        orden       = max_orden + 1,
        obligatoria = 1 if request.form.get('obligatoria') else 0
    )
    db.session.add(pregunta)
    db.session.flush()

    if tipo in ('opcion_unica', 'opcion_multiple'):
        lineas = [l.strip() for l in request.form.get('opciones', '').splitlines() if l.strip()]
        if len(lineas) < 2:
            db.session.rollback()
            flash('Las preguntas de opción necesitan al menos 2 opciones.', 'warning')
            return redirect(url_for('admin.detalle_encuesta', id=id))
        for i, texto_opcion in enumerate(lineas, start=1):
            db.session.add(Opciones(id_pregunta=pregunta.id_pregunta, texto=texto_opcion, orden=i))

    db.session.commit()
    flash('Pregunta agregada.', 'success')
    return redirect(url_for('admin.detalle_encuesta', id=id))


@admin.route('/admin/encuestas/<int:id>/preguntas/<int:id_pregunta>/eliminar', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def eliminar_pregunta(id, id_pregunta):
    pregunta = Preguntas.query.get_or_404(id_pregunta)
    if pregunta.id_encuesta != id:
        flash('No corresponde a esta encuesta.', 'danger')
        return redirect(url_for('admin.detalle_encuesta', id=id))
    db.session.delete(pregunta)
    db.session.commit()
    flash('Pregunta eliminada.', 'info')
    return redirect(url_for('admin.detalle_encuesta', id=id))


@admin.route('/admin/encuestas/<int:id>/publicar', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def publicar_encuesta(id):
    enc = Encuesta.query.get_or_404(id)
    if not Preguntas.query.filter_by(id_encuesta=id).first():
        flash('Agrega al menos una pregunta antes de publicar.', 'warning')
        return redirect(url_for('admin.detalle_encuesta', id=id))
    enc.estado = 'publicada'
    db.session.commit()
    flash('Encuesta publicada. Los egresados ya pueden responderla.', 'success')
    return redirect(url_for('admin.detalle_encuesta', id=id))


@admin.route('/admin/encuestas/<int:id>/cerrar', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def cerrar_encuesta(id):
    enc = Encuesta.query.get_or_404(id)
    enc.estado = 'cerrada'
    db.session.commit()
    flash('Encuesta cerrada. Ya no se puede responder.', 'info')
    return redirect(url_for('admin.detalle_encuesta', id=id))


@admin.route('/admin/encuestas/<int:id>/eliminar', methods=['POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def eliminar_encuesta(id):
    enc = Encuesta.query.get_or_404(id)
    if Respuestas.query.filter_by(id_encuesta=id).first():
        flash('No se puede eliminar una encuesta que ya tiene respuestas.', 'danger')
        return redirect(url_for('admin.detalle_encuesta', id=id))
    db.session.delete(enc)
    db.session.commit()
    flash('Encuesta eliminada.', 'info')
    return redirect(url_for('admin.encuestas'))


@admin.route('/admin/encuestas/<int:id>/resultados')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def resultados_encuesta(id):
    enc = Encuesta.query.get_or_404(id)
    preguntas = Preguntas.query.filter_by(id_encuesta=id).order_by(Preguntas.orden).all()

    id_facultad = request.args.get('id_facultad', type=int)
    id_programa = request.args.get('id_programa', type=int)

    rol_activo = current_user.rol_activo_nombre()
    alcance    = _alcance_programas(rol_activo, current_user.id_personal)

    if rol_activo == 'docente_responsable':
        id_facultad, id_programa = None, None
    elif rol_activo == 'coordinador':
        ids_fac_propias = _facultades_de_coordinador(current_user.id_personal)
        if id_facultad and id_facultad not in ids_fac_propias:
            id_facultad = None
        if id_programa and alcance is not None and id_programa not in alcance:
            id_programa = None

    ids_respondientes = _query_respuestas_filtradas(id, id_facultad, id_programa, ids_programas_forzado=alcance)\
        .with_entities(Respuestas.id_egresado).distinct()
    total_respondientes = ids_respondientes.count()

    resultados = []
    for p in preguntas:
        item = {'pregunta': p, 'tipo': p.tipo}
        base = _query_respuestas_filtradas(id, id_facultad, id_programa, ids_programas_forzado=alcance)\
                .filter(Respuestas.id_pregunta == p.id_pregunta)

        if p.tipo in ('opcion_unica', 'opcion_multiple'):
            conteo = base.join(Opciones, Respuestas.id_opcion == Opciones.id_opcion)\
                .with_entities(Opciones.texto, db.func.count(Respuestas.id_respuesta))\
                .group_by(Opciones.id_opcion, Opciones.texto)\
                .order_by(Opciones.orden).all()
            item['labels'] = [c[0] for c in conteo]
            item['data']   = [c[1] for c in conteo]

        elif p.tipo == 'si_no':
            si = base.filter(Respuestas.respuesta_booleana == 1).count()
            no = base.filter(Respuestas.respuesta_booleana == 0).count()
            item['labels'] = ['Sí', 'No']
            item['data']   = [si, no]

        elif p.tipo == 'numero':
            valores = [r[0] for r in base.filter(Respuestas.respuesta_numero != None)
                       .with_entities(Respuestas.respuesta_numero).all()]
            item['valores']  = valores
            item['promedio'] = round(sum(valores) / len(valores), 2) if valores else None
            item['minimo']   = min(valores) if valores else None
            item['maximo']   = max(valores) if valores else None

        elif p.tipo == 'texto':
            item['respuestas_texto'] = [r[0] for r in base
                .filter(Respuestas.respuesta_texto != None, Respuestas.respuesta_texto != '')
                .with_entities(Respuestas.respuesta_texto).all()]

        resultados.append(item)

    if rol_activo == 'coordinador':
        facultades = Facultades.query.filter(
            Facultades.id_facultad.in_(_facultades_de_coordinador(current_user.id_personal))
        ).order_by(Facultades.nombre).all()
    elif rol_activo == 'docente_responsable':
        facultades = []
    else:
        facultades = Facultades.query.order_by(Facultades.nombre).all()
    programas  = []
    if id_facultad:
        programas = ProgramasEstudio.query.filter_by(id_facultad=id_facultad)\
                                          .order_by(ProgramasEstudio.nombre).all()

    return render_template('admin/resultados_encuesta.html',
        encuesta=enc, resultados=resultados, total_respondientes=total_respondientes,
        facultades=facultades, programas=programas,
        id_facultad=id_facultad, id_programa=id_programa, rol_activo=rol_activo)


@admin.route('/admin/encuestas/<int:id>/programas-de-facultad')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador')
def programas_de_facultad(id):
    id_facultad = request.args.get('id_facultad', type=int)
    rol = current_user.rol_activo_nombre()
    alcance = _alcance_programas(rol, current_user.id_personal)
    programas_q = ProgramasEstudio.query.filter_by(id_facultad=id_facultad)
    if alcance is not None:
        programas_q = programas_q.filter(ProgramasEstudio.id_programa.in_(alcance))
    programas = programas_q.order_by(ProgramasEstudio.nombre).all()
    return jsonify([{'id': p.id_programa, 'nombre': p.nombre} for p in programas])


@admin.route('/admin/encuestas/<int:id>/exportar')
@login_required
@requiere_rol('administrador', 'utsag')
def exportar_encuesta(id):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    import io

    enc = Encuesta.query.get_or_404(id)
    preguntas = Preguntas.query.filter_by(id_encuesta=id).order_by(Preguntas.orden).all()

    id_facultad = request.args.get('id_facultad', type=int)
    id_programa = request.args.get('id_programa', type=int)

    rol_activo = current_user.rol_activo_nombre()
    alcance    = _alcance_programas(rol_activo, current_user.id_personal)

    if rol_activo == 'docente_responsable':
        id_facultad, id_programa = None, None
    elif rol_activo == 'coordinador':
        ids_fac_propias = _facultades_de_coordinador(current_user.id_personal)
        if id_facultad and id_facultad not in ids_fac_propias:
            id_facultad = None
        if id_programa and alcance is not None and id_programa not in alcance:
            id_programa = None

    ids_egresados = [r[0] for r in _query_respuestas_filtradas(id, id_facultad, id_programa, ids_programas_forzado=alcance)
                      .with_entities(Respuestas.id_egresado).distinct()
                      .order_by(Respuestas.id_egresado).all()]

    todas = _query_respuestas_filtradas(id, id_facultad, id_programa, ids_programas_forzado=alcance).all()
    mapa = {}
    for r in todas:
        mapa.setdefault((r.id_egresado, r.id_pregunta), []).append(r)

    def formatear(celdas, tipo):
        if not celdas:
            return ''
        if tipo == 'texto':
            return celdas[0].respuesta_texto or ''
        if tipo == 'numero':
            return celdas[0].respuesta_numero if celdas[0].respuesta_numero is not None else ''
        if tipo == 'si_no':
            v = celdas[0].respuesta_booleana
            return 'Sí' if v == 1 else ('No' if v == 0 else '')
        if tipo == 'opcion_unica':
            return celdas[0].opcion.texto if celdas[0].opcion else ''
        if tipo == 'opcion_multiple':
            return ', '.join(c.opcion.texto for c in celdas if c.opcion)
        return ''

    wb = Workbook()
    ws = wb.active
    ws.title = 'Resultados'

    ws.append(['N°'] + [p.texto for p in preguntas])
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='003876', end_color='003876', fill_type='solid')
        cell.alignment = Alignment(horizontal='center', wrap_text=True)

    def celda_segura(valor):
        if isinstance(valor, str) and valor.lstrip().startswith(('=', '+', '-', '@')):
            return "'" + valor
        return valor

    for i, id_egresado in enumerate(ids_egresados, start=1):
        fila = [i]
        for p in preguntas:
            fila.append(celda_segura(formatear(mapa.get((id_egresado, p.id_pregunta), []), p.tipo)))
        ws.append(fila)

    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 40)

    mem = io.BytesIO()
    wb.save(mem)
    mem.seek(0)
    sufijo = ''
    if id_programa:
        p = ProgramasEstudio.query.get(id_programa)
        sufijo = f"_{p.codigo}" if p else ''
    elif id_facultad:
        f = Facultades.query.get(id_facultad)
        sufijo = f"_{f.codigo}" if f else ''
    nombre_archivo = f"encuesta_{enc.anio}_{enc.nombre.replace(' ', '_')[:30]}{sufijo}.xlsx"
    return send_file(mem, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                      as_attachment=True, download_name=nombre_archivo)