"""Portal exclusivo para empresas validadas: ofertas propias y revisión de postulantes."""

from functools import wraps
from datetime import date, datetime, timezone
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.empresa import empresa
from app.extensions import db
from app.models import (
    Empresas, OfertasLaborales, Postulaciones,
    AutorizacionesDocumentales, DocumentosEgresado, Usuarios
)
from app.services.validaciones_service import limpiar_texto, parse_fecha_iso
from app.services.auditoria_service import registrar_auditoria
from app.services.notificaciones_service import crear_notificacion


ESTADOS_POSTULACION_EMPRESA = {
    'enviada': 'Recibida',
    'en_revision': 'En revisión',
    'preseleccionado': 'Preseleccionado',
    'entrevista': 'Entrevista',
    'seleccionado': 'Seleccionado',
    'no_seleccionado': 'No seleccionado',
}


def solo_empresa(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if (
            not current_user.is_authenticated
            or not current_user.es_empresa()
            or current_user.rol_activo_nombre() != 'empresa'
        ):
            flash('Acceso exclusivo para cuentas empresariales.', 'danger')
            return redirect(url_for('auth.login'))
        emp = db.session.get(Empresas, current_user.id_empresa)
        if not emp or emp.estado != 'activa':
            flash('Tu empresa aún está pendiente de validación administrativa.', 'warning')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorado


@empresa.route('/empresa/panel')
@login_required
@solo_empresa
def panel():
    emp = db.session.get(Empresas, current_user.id_empresa)
    ofertas = OfertasLaborales.query.filter_by(id_empresa=emp.id_empresa)\
        .order_by(OfertasLaborales.fecha_publicacion.desc(), OfertasLaborales.id_oferta.desc()).all()

    ids_ofertas = [o.id_oferta for o in ofertas]
    postulaciones = (
        Postulaciones.query.filter(Postulaciones.id_oferta.in_(ids_ofertas)).all()
        if ids_ofertas else []
    )
    conteo_por_oferta = {}
    for p in postulaciones:
        conteo_por_oferta[p.id_oferta] = conteo_por_oferta.get(p.id_oferta, 0) + 1

    kpi = {
        'ofertas_activas': sum(1 for o in ofertas if o.activa == 1 and o.fecha_vencimiento >= date.today()),
        'ofertas_total': len(ofertas),
        'postulaciones_total': len(postulaciones),
        'en_proceso': sum(1 for p in postulaciones if p.estado in ('enviada', 'en_revision', 'preseleccionado', 'entrevista')),
    }
    return render_template(
        'empresa/panel.html',
        empresa=emp,
        ofertas=ofertas,
        conteo_por_oferta=conteo_por_oferta,
        kpi=kpi,
    )


@empresa.route('/empresa/ofertas/nueva', methods=['GET', 'POST'])
@login_required
@solo_empresa
def nueva_oferta():
    emp = db.session.get(Empresas, current_user.id_empresa)
    if request.method == 'POST':
        titulo = limpiar_texto(request.form.get('titulo'), 255)
        if not titulo:
            flash('El nombre del puesto es obligatorio.', 'warning')
            return render_template('empresa/nueva_oferta.html', empresa=emp, form_data=request.form)

        try:
            fecha_venc = parse_fecha_iso(request.form.get('fecha_vencimiento'), obligatoria=True)
            if fecha_venc < date.today():
                raise ValueError('La fecha de cierre no puede ser anterior a hoy.')
        except ValueError as exc:
            flash(str(exc), 'warning')
            return render_template('empresa/nueva_oferta.html', empresa=emp, form_data=request.form)

        oferta = OfertasLaborales(
            id_empresa=emp.id_empresa,
            titulo=titulo,
            empresa=emp.nombre_display(),
            telefono=emp.telefono,
            descripcion=limpiar_texto(request.form.get('descripcion'), 4000) or None,
            requisitos=limpiar_texto(request.form.get('requisitos'), 3000) or None,
            carrera_requerida=limpiar_texto(request.form.get('carrera_requerida'), 150) or None,
            experiencia_requerida=limpiar_texto(request.form.get('experiencia_requerida'), 150) or None,
            funciones=limpiar_texto(request.form.get('funciones'), 3000) or None,
            modalidad=limpiar_texto(request.form.get('modalidad'), 80) or None,
            tipo_oferta=limpiar_texto(request.form.get('tipo_oferta'), 80) or 'Empleo',
            jornada=limpiar_texto(request.form.get('jornada'), 80) or None,
            remuneracion=limpiar_texto(request.form.get('remuneracion'), 100) or None,
            ubicacion=limpiar_texto(request.form.get('ubicacion'), 150) or None,
            fuente='manual',
            fecha_publicacion=date.today(),
            fecha_vencimiento=fecha_venc,
            activa=1,
        )
        db.session.add(oferta)
        db.session.commit()
        registrar_auditoria('publicar_oferta_empresa', 'bolsa_laboral', 'ofertas_laborales', oferta.id_oferta)
        flash('Vacante publicada en la bolsa laboral NEXO UNDAC.', 'success')
        return redirect(url_for('empresa.panel'))

    return render_template('empresa/nueva_oferta.html', empresa=emp, form_data=None)


@empresa.route('/empresa/ofertas/<int:id_oferta>/toggle', methods=['POST'])
@login_required
@solo_empresa
def toggle_oferta(id_oferta):
    oferta = OfertasLaborales.query.get_or_404(id_oferta)
    if oferta.id_empresa != current_user.id_empresa:
        abort(403)
    oferta.activa = 0 if oferta.activa == 1 else 1
    db.session.commit()
    registrar_auditoria('toggle_oferta_empresa', 'bolsa_laboral', 'ofertas_laborales', oferta.id_oferta)
    flash('Estado de la oferta actualizado.', 'info')
    return redirect(url_for('empresa.panel'))


@empresa.route('/empresa/ofertas/<int:id_oferta>/postulaciones')
@login_required
@solo_empresa
def ver_postulaciones(id_oferta):
    oferta = OfertasLaborales.query.get_or_404(id_oferta)
    if oferta.id_empresa != current_user.id_empresa:
        abort(403)

    postulaciones = Postulaciones.query.filter_by(id_oferta=oferta.id_oferta)\
        .order_by(Postulaciones.fecha.desc()).all()

    docs_autorizados_por_post = {}
    for p in postulaciones:
        auts = (
            AutorizacionesDocumentales.query
            .filter_by(
                id_postulacion=p.id_postulacion,
                id_empresa=current_user.id_empresa,
                autorizado=1,
                revocado_en=None,
            )
            .all()
        )
        docs_autorizados_por_post[p.id_postulacion] = [a.documento for a in auts if a.documento]

    return render_template(
        'empresa/postulaciones.html',
        oferta=oferta,
        postulaciones=postulaciones,
        docs_por_post=docs_autorizados_por_post,
        estados=ESTADOS_POSTULACION_EMPRESA,
    )


@empresa.route('/empresa/postulaciones/<int:id_postulacion>/estado', methods=['POST'])
@login_required
@solo_empresa
def cambiar_estado_postulacion(id_postulacion):
    post = Postulaciones.query.get_or_404(id_postulacion)
    if not post.oferta or post.oferta.id_empresa != current_user.id_empresa:
        abort(403)
    if post.estado == 'retirada':
        flash('El postulante retiró su candidatura.', 'warning')
        return redirect(url_for('empresa.ver_postulaciones', id_oferta=post.id_oferta))

    nuevo_estado = request.form.get('estado', '').strip()
    if nuevo_estado not in ESTADOS_POSTULACION_EMPRESA:
        flash('Estado inválido.', 'warning')
        return redirect(url_for('empresa.ver_postulaciones', id_oferta=post.id_oferta))

    post.estado = nuevo_estado
    post.observacion_empresa = limpiar_texto(request.form.get('observacion_empresa'), 500) or None
    post.actualizado_en = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()

    registrar_auditoria(
        'actualizar_postulacion_empresa', 'bolsa_laboral', 'postulaciones',
        post.id_postulacion, detalle=nuevo_estado
    )

    u_egr = Usuarios.query.filter_by(id_egresado=post.id_egresado).first()
    if u_egr:
        etiqueta = ESTADOS_POSTULACION_EMPRESA.get(nuevo_estado, nuevo_estado)
        crear_notificacion(
            u_egr.id_usuario,
            titulo=f'Actualización en postulación: {etiqueta}',
            mensaje=f'Tu postulación a "{post.oferta.titulo}" cambió a estado: {etiqueta}.',
            tipo='postulacion',
            enlace=url_for('egresado.mi_seguimiento'),
        )

    flash('Estado de postulación actualizado.', 'success')
    return redirect(url_for('empresa.ver_postulaciones', id_oferta=post.id_oferta))
