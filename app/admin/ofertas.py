# app/admin/ofertas.py
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.admin import admin
from app.admin.helpers import requiere_rol
from app.extensions import db
from app.models import Empresas, OfertasLaborales
from datetime import date


@admin.route('/admin/ofertas')
@login_required
@requiere_rol('administrador')
def ofertas():
    buscar = request.args.get('buscar', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    estado = request.args.get('estado', 'activa')

    OfertasLaborales.query.filter(
        OfertasLaborales.fecha_vencimiento < date.today(),
        OfertasLaborales.activa == 1
    ).update({'activa': 0})
    db.session.commit()

    q = OfertasLaborales.query
    if current_user.rol_activo_nombre() == 'coordinador':
        q = q.filter(OfertasLaborales.id_creado_por == current_user.id_personal)
    q = q.filter_by(activa=1) if estado == 'activa' else q.filter_by(activa=0)

    if buscar:
        like = f'%{buscar}%'
        q = q.filter(db.or_(
            OfertasLaborales.titulo.ilike(like),
            OfertasLaborales.empresa.ilike(like),
            OfertasLaborales.ubicacion.ilike(like),
        ))

    paginado = q.order_by(OfertasLaborales.fecha_publicacion.desc())\
                .paginate(page=pagina, per_page=15, error_out=False)

    return render_template('admin/ofertas.html',
        ofertas=paginado.items, paginacion=paginado,
        buscar=buscar, estado=estado, pagina=pagina)


@admin.route('/admin/ofertas/nueva', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador')
def nueva_oferta():
    if request.method == 'POST':
        id_empresa = request.form.get('id_empresa', '').strip() or None
        if id_empresa and not Empresas.query.filter_by(id_empresa=id_empresa, estado='activa').first():
            flash('Selecciona una empresa activa y registrada.', 'danger')
            return redirect(url_for('admin.nueva_oferta'))
        empresa_texto = request.form.get('empresa', '').strip() or None

        ruta_imagen = None
        imagen = request.files.get('imagen')
        if imagen and imagen.filename:
            from app.helpers import guardar_archivo
            ruta_imagen = guardar_archivo(imagen, 'ofertas')

        oferta = OfertasLaborales(
            id_creado_por     = current_user.id_personal,
            id_empresa        = id_empresa,
            titulo            = request.form.get('titulo', '').strip(),
            empresa           = empresa_texto,
            telefono          = request.form.get('telefono', '').strip() or None,
            tipo_oferta       = request.form.get('tipo_oferta', '').strip() or 'Empleo',
            descripcion       = request.form.get('descripcion', '').strip() or None,
            requisitos        = request.form.get('requisitos', '').strip() or None,
            funciones         = request.form.get('funciones', '').strip() or None,
            modalidad         = request.form.get('modalidad', '').strip() or None,
            jornada           = request.form.get('jornada', '').strip() or None,
            remuneracion      = request.form.get('remuneracion', '').strip() or None,
            ubicacion         = request.form.get('ubicacion', '').strip() or None,
            ruta_imagen       = ruta_imagen,
            url_original      = request.form.get('url_original', '').strip() or None,
            fuente            = 'manual',
            fecha_publicacion = date.today(),
            fecha_vencimiento = request.form.get('fecha_vencimiento'),
            activa            = 1
        )
        db.session.add(oferta)
        db.session.commit()
        flash('Oferta publicada correctamente.', 'success')
        return redirect(url_for('admin.ofertas'))

    empresas = Empresas.query.filter_by(estado='activa').order_by(Empresas.razon_social).all()
    return render_template('admin/nueva_oferta.html', empresas=empresas)


@admin.route('/admin/ofertas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador')
def editar_oferta(id):
    oferta = OfertasLaborales.query.get_or_404(id)
    if current_user.rol_activo_nombre() == 'coordinador' and oferta.id_creado_por != current_user.id_personal:
        from flask import abort
        abort(403)

    if request.method == 'POST':
        id_empresa_nuevo = request.form.get('id_empresa', '').strip() or None
        if id_empresa_nuevo and not Empresas.query.filter_by(id_empresa=id_empresa_nuevo, estado='activa').first():
            flash('Selecciona una empresa activa y registrada.', 'danger')
            return redirect(url_for('admin.editar_oferta', id=id))
        oferta.id_empresa        = id_empresa_nuevo
        oferta.empresa           = request.form.get('empresa', '').strip() or None
        oferta.telefono          = request.form.get('telefono', '').strip() or None
        oferta.titulo            = request.form.get('titulo', '').strip()
        oferta.tipo_oferta       = request.form.get('tipo_oferta', '').strip() or 'Empleo'
        oferta.descripcion       = request.form.get('descripcion', '').strip() or None
        oferta.requisitos        = request.form.get('requisitos', '').strip() or None
        oferta.funciones         = request.form.get('funciones', '').strip() or None
        oferta.modalidad         = request.form.get('modalidad', '').strip() or None
        oferta.jornada           = request.form.get('jornada', '').strip() or None
        oferta.remuneracion      = request.form.get('remuneracion', '').strip() or None
        oferta.ubicacion         = request.form.get('ubicacion', '').strip() or None
        oferta.url_original      = request.form.get('url_original', '').strip() or None
        oferta.fecha_vencimiento = request.form.get('fecha_vencimiento')
        oferta.activa            = 1 if request.form.get('activa') else 0

        imagen = request.files.get('imagen')
        if imagen and imagen.filename:
            from app.helpers import guardar_archivo
            nueva_ruta = guardar_archivo(imagen, 'ofertas')
            if nueva_ruta:
                oferta.ruta_imagen = nueva_ruta

        db.session.commit()
        flash('Oferta actualizada.', 'success')
        return redirect(url_for('admin.ofertas'))

    empresas = Empresas.query.filter_by(estado='activa').order_by(Empresas.razon_social).all()
    return render_template('admin/editar_oferta.html', oferta=oferta, empresas=empresas)


@admin.route('/admin/ofertas/<int:id>/toggle', methods=['POST'])
@login_required
@requiere_rol('administrador')
def toggle_oferta(id):
    oferta = OfertasLaborales.query.get_or_404(id)
    if current_user.rol_activo_nombre() == 'coordinador' and oferta.id_creado_por != current_user.id_personal:
        from flask import abort
        abort(403)
    oferta.activa = 0 if oferta.activa else 1
    db.session.commit()
    estado = 'activada' if oferta.activa else 'desactivada'
    flash(f'Oferta {estado}.', 'info')
    return redirect(url_for('admin.ofertas',
        estado=request.form.get('estado', 'activa'),
        pagina=request.form.get('pagina', 1)))

@admin.route('/admin/ofertas/postulaciones')
@login_required
@requiere_rol('administrador')
def ver_postulaciones():
    from flask_login import current_user
    from app.models import Postulaciones, Egresados, Curriculas
    from app.ambito import ids_programa_sistemas
    from app.utils.v8_csrf import token_v8
    from app.utils.v8_db import tablas_v8_disponibles
    if not tablas_v8_disponibles():
        flash('La sección de postulaciones requiere aplicar primero la migración SQL V8.', 'warning')
        return redirect(url_for('admin.ofertas'))
    consulta = (Postulaciones.query
        .join(OfertasLaborales, Postulaciones.id_oferta == OfertasLaborales.id_oferta)
        .join(Egresados, Postulaciones.id_egresado == Egresados.id_egresado)
        .join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula))
    # Proyecto exclusivo Sistemas: no mostrar expedientes de otras carreras,
    # aunque el administrador tenga permisos técnicos globales.
    ids_sistemas = ids_programa_sistemas()
    if ids_sistemas is not None:
        consulta = consulta.filter(Curriculas.id_programa.in_(ids_sistemas))
    if current_user.rol_activo_nombre() == 'coordinador':
        consulta = consulta.filter(OfertasLaborales.id_creado_por == current_user.id_personal)
    filas = consulta.order_by(Postulaciones.fecha.desc()).limit(150).all()
    return render_template('admin/postulaciones.html', filas=filas, rol_activo=current_user.rol_activo_nombre(), csrf_admin=token_v8())


@admin.route('/admin/ofertas/postulaciones/<int:id_postulacion>/estado', methods=['POST'])
@login_required
@requiere_rol('administrador')
def cambiar_estado_postulacion(id_postulacion):
    from flask_login import current_user
    from app.utils.v8_csrf import validar_v8
    validar_v8()
    from app.models import Postulaciones
    from app.utils.v8_db import tablas_v8_disponibles
    if not tablas_v8_disponibles():
        flash('La migración SQL V8 está pendiente.', 'warning')
        return redirect(url_for('admin.ofertas'))
    fila = Postulaciones.query.get_or_404(id_postulacion)
    from app.ambito import es_egresado_en_ambito
    from flask import abort
    if not es_egresado_en_ambito(fila.egresado):
        abort(403)
    if current_user.rol_activo_nombre() == 'coordinador' and fila.oferta.id_creado_por != current_user.id_personal:
        from flask import abort
        abort(403)
    estado = request.form.get('estado')
    if estado not in ('enviada', 'en_revision'):
        flash('Estado no permitido.', 'danger')
    else:
        fila.estado = estado
        db.session.commit()
        flash('Estado de la postulación actualizado.', 'success')
    return redirect(url_for('admin.ver_postulaciones'))
