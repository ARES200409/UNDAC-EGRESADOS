# app/egresado/routes.py
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, send_file, session, abort
from flask_login import login_required, current_user
from app.egresado import egresado
from app.extensions import db
from app.models import (
    Egresados, Empleos, Empresas, Usuarios, TrayectoriaAcademica,
    Certificados, Habilidades, Sectores, OfertasLaborales, OfertasGuardadas,
    Postulaciones, DocumentosEgresado, AutorizacionesDocumentales
)
from app.helpers import guardar_archivo
from app.services.perfil_service import calcular_completitud_perfil, ETIQUETAS_SITUACION
from app.services.auditoria_service import registrar_auditoria
from app.services.validaciones_service import parse_fecha_iso
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import or_
import secrets, hmac
from app.utils.v8_db import tablas_v8_disponibles


# ============================================
# UTILIDADES Y DECORADORES
# ============================================

def solo_egresado(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_egresado():
            flash('Acceso no permitido.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorado


# ============================================
# PERFIL
# ============================================

@egresado.route('/perfil')
@login_required
@solo_egresado
def perfil():
    e = Egresados.query.get(current_user.id_egresado)
    completitud = calcular_completitud_perfil(e)
    return render_template(
        'egresado/perfil.html',
        e=e,
        completitud=completitud,
        etiquetas_situacion=ETIQUETAS_SITUACION,
    )


@egresado.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
@solo_egresado
def editar_perfil():
    e = Egresados.query.get(current_user.id_egresado)

    if request.method == 'POST':
        correo_inst = request.form.get('correo_institucional', '').strip()
        if correo_inst and correo_inst != e.correo_institucional:
            existe = Usuarios.query.filter(
                Usuarios.correo == correo_inst,
                Usuarios.id_usuario != current_user.id_usuario
            ).first()
            if existe:
                flash('Ese correo ya está en uso por otra cuenta.', 'danger')
                return render_template('egresado/editar_perfil.html', e=e)
            e.correo_institucional = correo_inst
            current_user.correo    = correo_inst

        e.correo_personal = request.form.get('correo_personal', '').strip()
        e.telefono        = request.form.get('telefono', '').strip()
        e.distrito        = request.form.get('distrito', '').strip()
        e.provincia       = request.form.get('provincia', '').strip()
        e.region          = request.form.get('region', '').strip()
        e.pais            = request.form.get('pais', '').strip() or 'Perú'
        e.linkedin        = request.form.get('linkedin', '').strip()
        e.facebook        = request.form.get('facebook', '').strip()
        e.tiktok          = request.form.get('tiktok', '').strip()

        if 'titulo_cv' in request.form:
            e.titulo_cv = request.form.get('titulo_cv', '').strip()[:150] or None
        if 'perfil_profesional' in request.form:
            e.perfil_profesional = request.form.get('perfil_profesional', '').strip()[:3000] or None
        if 'situacion_laboral' in request.form:
            sit = request.form.get('situacion_laboral', '').strip()
            if sit in ETIQUETAS_SITUACION:
                e.situacion_laboral = sit
        if 'control_privacidad_presente' in request.form:
            e.perfil_publico = 1 if request.form.get('perfil_publico') == '1' else 0
        e.actualizado_en = datetime.now(timezone.utc).replace(tzinfo=None)

        anio_egreso = request.form.get('anio_egreso', '').strip()
        if anio_egreso:
            try:
                anio_egreso_int = int(anio_egreso)
                if 1990 <= anio_egreso_int <= 2100:
                    e.anio_egreso = anio_egreso_int
            except ValueError:
                pass  # si escriben algo no numérico, se ignora silenciosamente

        e.periodo = request.form.get('periodo', '').strip() or None

        foto = request.files.get('foto')
        if foto and foto.filename:
            ruta = guardar_archivo(foto, 'fotos')
            if ruta:
                e.foto = ruta
            else:
                flash('Formato de foto no permitido. Usa PNG, JPG o WEBP.', 'warning')

        db.session.commit()
        registrar_auditoria('editar_perfil', 'egresado', 'egresados', e.id_egresado)
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('egresado.perfil'))

    habilidades_l = Habilidades.query.filter_by(id_egresado=e.id_egresado, tipo='habilidad').all()
    intereses_l   = Habilidades.query.filter_by(id_egresado=e.id_egresado, tipo='interes').all()
    return render_template(
        'egresado/editar_perfil.html',
        e=e,
        habilidades=habilidades_l,
        intereses=intereses_l,
        etiquetas_situacion=ETIQUETAS_SITUACION,
    )


# ============================================
# EMPLEOS
# ============================================

@egresado.route('/empleos')
@login_required
@solo_egresado
def empleos():
    lista = Empleos.query.filter_by(id_egresado=current_user.id_egresado)\
                         .order_by(Empleos.es_actual.desc(), Empleos.fecha_inicio.desc()).all()
    return render_template('egresado/empleos.html', empleos=lista)


@egresado.route('/empleos/nuevo', methods=['GET', 'POST'])
@login_required
@solo_egresado
def nuevo_empleo():
    sectores = Sectores.query.order_by(Sectores.nombre).all()
    empresas = Empresas.query.filter_by(estado='activa').order_by(Empresas.razon_social).all()

    if request.method == 'POST':
        id_empresa = request.form.get('id_empresa', type=int)

        # Si no seleccionó una empresa existente, creamos/sugerimos una nueva
        if not id_empresa:
            if not request.form.get('id_sector', type=int) or not Sectores.query.get(request.form.get('id_sector', type=int)):
                flash('Selecciona un sector económico válido para la nueva empresa.', 'warning')
                return render_template('egresado/nuevo_empleo.html', empresas=empresas, sectores=sectores, form_data=request.form)
            ruc = request.form.get('ruc', '').strip() or None
            razon_social = request.form.get('razon_social', '').strip()

            if not razon_social:
                flash('La razón social de la empresa es obligatoria.', 'danger')
                return render_template('egresado/nuevo_empleo.html', empresas=empresas, sectores=sectores, form_data=request.form)

            if ruc:
                emp_existente = Empresas.query.filter_by(ruc=ruc).first()
                if emp_existente:
                    flash(f'El RUC ingresado ya pertenece a la empresa: {emp_existente.nombre_display()}', 'warning')
                    return render_template('egresado/nuevo_empleo.html', empresas=empresas, sectores=sectores, form_data=request.form)

            # Crear la empresa en estado pendiente
            nueva_emp = Empresas(
                ruc=ruc,
                razon_social=razon_social,
                nombre_comercial=request.form.get('nombre_comercial', '').strip() or None,
                id_sector=request.form.get('id_sector', type=int),
                tipo_empresa=request.form.get('tipo_empresa', '').strip() or None,
                direccion=request.form.get('direccion', '').strip() or None,
                distrito=request.form.get('distrito', '').strip() or None,
                provincia=request.form.get('provincia', '').strip() or None,
                region=request.form.get('region', '').strip() or None,
                pais=request.form.get('pais', '').strip() or 'Perú',
                telefono=request.form.get('telefono_empresa', '').strip() or None,
                sitio_web=request.form.get('sitio_web', '').strip() or None,
                estado='pendiente',
                sugerido_por=current_user.id_egresado
            )
            db.session.add(nueva_emp)
            db.session.flush()  # Para obtener el id_empresa generado
            id_empresa = nueva_emp.id_empresa

        if id_empresa and not Empresas.query.get(id_empresa):
            flash('La empresa seleccionada no existe.', 'danger')
            return redirect(url_for('egresado.nuevo_empleo'))

        # Crear el empleo con validación estricta de fechas y campos obligatorios
        cargo = request.form.get('cargo', '').strip()
        if not cargo:
            flash('El cargo desempeñado es obligatorio.', 'warning')
            return render_template('egresado/nuevo_empleo.html', empresas=empresas, sectores=sectores, form_data=request.form)

        es_actual = 1 if request.form.get('es_actual') else 0
        try:
            fecha_inicio = parse_fecha_iso(request.form.get('fecha_inicio'), obligatoria=True)
            fecha_fin = None if es_actual else parse_fecha_iso(request.form.get('fecha_fin'), obligatoria=False)
            if fecha_fin and fecha_fin < fecha_inicio:
                raise ValueError('La fecha de fin no puede ser anterior a la fecha de inicio.')
        except ValueError as exc:
            flash(str(exc), 'warning')
            return render_template('egresado/nuevo_empleo.html', empresas=empresas, sectores=sectores, form_data=request.form)

        modalidad = request.form.get('modalidad', '').strip() or None
        if modalidad not in (None, 'presencial', 'remoto', 'hibrido'):
            modalidad = None
        rel_val = request.form.get('relacion_carrera')
        relacion_carrera = 1 if rel_val == '1' else (0 if rel_val == '0' else None)

        empleo = Empleos(
            id_egresado=current_user.id_egresado,
            id_empresa=id_empresa,
            cargo=cargo,
            tipo_contrato=request.form.get('tipo_contrato', '').strip() or None,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            es_actual=es_actual,
            funciones=request.form.get('funciones', '').strip() or None,
            relacion_carrera=relacion_carrera,
            modalidad=modalidad,
            rango_remuneracion=request.form.get('rango_remuneracion', '').strip()[:80] or None,
            es_independiente=1 if request.form.get('es_independiente') else 0,
        )
        db.session.add(empleo)
        db.session.commit()

        flash('Empleo registrado correctamente.', 'success')
        return redirect(url_for('egresado.empleos'))

    return render_template('egresado/nuevo_empleo.html', empresas=empresas, sectores=sectores, form_data=None)


@egresado.route('/empleos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@solo_egresado
def editar_empleo(id):
    empleo = Empleos.query.get_or_404(id)
    if empleo.id_egresado != current_user.id_egresado:
        flash('No tienes permiso para editar este empleo.', 'danger')
        return redirect(url_for('egresado.empleos'))

    empresas = Empresas.query.filter_by(estado='activa').order_by(Empresas.razon_social).all()

    if request.method == 'POST':
        id_empresa = request.form.get('id_empresa', type=int)
        if not id_empresa or not Empresas.query.get(id_empresa):
            flash('Selecciona una empresa válida.', 'warning')
            return redirect(url_for('egresado.editar_empleo', id=id))
        if not request.form.get('cargo', '').strip() or not request.form.get('fecha_inicio'):
            flash('Debes indicar cargo y fecha de inicio.', 'warning')
            return redirect(url_for('egresado.editar_empleo', id=id))
        es_actual = 1 if request.form.get('es_actual') else 0
        fecha_fin = None if es_actual else (request.form.get('fecha_fin') or None)

        empleo.id_empresa = request.form.get('id_empresa', type=int)
        empleo.cargo = request.form.get('cargo', '').strip()
        empleo.tipo_contrato = request.form.get('tipo_contrato', '').strip() or None
        empleo.fecha_inicio = request.form.get('fecha_inicio')
        empleo.fecha_fin = fecha_fin
        empleo.es_actual = es_actual
        empleo.funciones = request.form.get('funciones', '').strip() or None

        db.session.commit()
        flash('Empleo actualizado correctamente.', 'success')
        return redirect(url_for('egresado.empleos'))

    return render_template('egresado/editar_empleo.html', empleo=empleo, empresas=empresas)


@egresado.route('/empleos/<int:id>/eliminar', methods=['POST'])
@login_required
@solo_egresado
def eliminar_empleo(id):
    empleo = Empleos.query.get_or_404(id)
    if empleo.id_egresado != current_user.id_egresado:
        flash('No tienes permiso para eliminar este empleo.', 'danger')
        return redirect(url_for('egresado.empleos'))

    db.session.delete(empleo)
    db.session.commit()
    flash('Empleo eliminado.', 'info')
    return redirect(url_for('egresado.empleos'))

# ============================================
# TRAYECTORIA ACADEMICA (TITULOS Y GRADOS)
# ============================================

@egresado.route('/trayectoria')
@login_required
@solo_egresado
def trayectoria():
    e = Egresados.query.get(current_user.id_egresado)
    logros = TrayectoriaAcademica.query.filter_by(id_egresado=e.id_egresado)\
                                       .order_by(TrayectoriaAcademica.fecha_obtencion).all()
    return render_template('egresado/trayectoria.html', e=e, logros=logros)


@egresado.route('/trayectoria/<int:id>/eliminar', methods=['POST'])
@login_required
@solo_egresado
def eliminar_logro(id):
    logro = TrayectoriaAcademica.query.get_or_404(id)
    if logro.id_egresado != current_user.id_egresado:
        flash('No tienes permiso.', 'danger')
        return redirect(url_for('egresado.trayectoria'))
    db.session.delete(logro)
    db.session.commit()
    flash('Registro eliminado.', 'info')
    return redirect(url_for('egresado.trayectoria'))


@egresado.route('/trayectoria/nuevo', methods=['GET', 'POST'])
@login_required
@solo_egresado
def nuevo_grado_titulo():
    e = Egresados.query.get(current_user.id_egresado)

    if request.method == 'POST':
        tipo = request.form.get('tipo', '').strip()

        logro = TrayectoriaAcademica(
            id_egresado     = e.id_egresado,
            tipo            = tipo,  # 'bachiller' | 'titulado' | 'maestria' | 'doctorado' | 'phd'
            grado_titulo    = request.form.get('grado_titulo', '').strip(),
            institucion     = request.form.get('institucion', '').strip() or 'Universidad Nacional Daniel Alcides Carrión',
            fecha_obtencion = request.form.get('fecha_obtencion'),
            fuente          = 'declaracion_egresado',
        )
        db.session.add(logro)
        db.session.commit()
        # El trigger `actualizar_nivel_egresado` ya actualizó es_bachiller,
        # es_titulado, nivel_maximo, etc. en la fila de `egresados`.
        # Refrescamos el objeto en memoria para que refleje esos cambios.
        db.session.refresh(e)

        flash('Grado o título registrado correctamente.', 'success')
        return redirect(url_for('egresado.trayectoria'))

    nombre_programa = e.curricula.programa.nombre if e.curricula else ''
    return render_template('egresado/nuevo_grado_titulo.html', e=e, nombre_programa=nombre_programa)


# ============================================
# Certificados y especializaciones
# ============================================

@egresado.route('/certificados')
@login_required
@solo_egresado
def certificados():
    e = Egresados.query.get(current_user.id_egresado)
    lista = Certificados.query.filter_by(id_egresado=e.id_egresado)\
                              .order_by(Certificados.fecha_emision.desc()).all()
    externos = [c for c in lista if c.tipo == 'externo']
    internos = [c for c in lista if c.tipo == 'interno']
    return render_template('egresado/certificados.html', externos=externos, internos=internos)


@egresado.route('/certificados/nuevo', methods=['GET', 'POST'])
@login_required
@solo_egresado
def nuevo_certificado():
    if request.method == 'POST':
        cert = Certificados(
            id_egresado         = current_user.id_egresado,
            nombre              = request.form.get('nombre', '').strip(),
            institucion_emisora = request.form.get('institucion_emisora', '').strip(),
            tipo                = request.form.get('tipo', 'externo'),
            categoria           = request.form.get('categoria', 'curso'),
            nivel_idioma        = request.form.get('nivel_idioma') or None,
            fecha_emision       = request.form.get('fecha_emision') or None,
            url_credencial      = request.form.get('url_credencial', '').strip() or None,
        )
        db.session.add(cert)
        db.session.commit()
        flash('Certificado registrado correctamente.', 'success')
        return redirect(url_for('egresado.certificados'))

    return render_template('egresado/nuevo_certificado.html')


@egresado.route('/certificados/<int:id>/eliminar', methods=['POST'])
@login_required
@solo_egresado
def eliminar_certificado(id):
    cert = Certificados.query.get_or_404(id)
    if cert.id_egresado != current_user.id_egresado:
        flash('No tienes permiso.', 'danger')
        return redirect(url_for('egresado.certificados'))
    db.session.delete(cert)
    db.session.commit()
    flash('Certificado eliminado.', 'info')
    return redirect(url_for('egresado.certificados'))


# ============================================
# HABILIDADES E INTERESES (parte del perfil)
# ============================================
from flask import jsonify
@egresado.route('/habilidades/nueva', methods=['POST'])
@login_required
@solo_egresado
def nueva_habilidad():
    nombre = request.form.get('nombre', '').strip()
    tipo   = request.form.get('tipo', 'habilidad')

    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not nombre:
        if es_ajax:
            return jsonify({'ok': False, 'error': 'El nombre no puede estar vacío.'}), 400
        flash('El nombre no puede estar vacío.', 'warning')
        return redirect(url_for('egresado.editar_perfil'))

    h = Habilidades(id_egresado=current_user.id_egresado, nombre=nombre, tipo=tipo)
    db.session.add(h)
    db.session.commit()

    if es_ajax:
        return jsonify({'ok': True, 'id_habilidad': h.id_habilidad, 'nombre': h.nombre, 'tipo': h.tipo})

    flash('Agregado correctamente.', 'success')
    return redirect(url_for('egresado.editar_perfil'))


@egresado.route('/habilidades/<int:id>/eliminar', methods=['POST'])
@login_required
@solo_egresado
def eliminar_habilidad(id):
    h = Habilidades.query.get_or_404(id)
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if h.id_egresado != current_user.id_egresado:
        if es_ajax:
            return jsonify({'ok': False, 'error': 'No tienes permiso.'}), 403
        flash('No tienes permiso.', 'danger')
        return redirect(url_for('egresado.editar_perfil'))

    db.session.delete(h)
    db.session.commit()

    if es_ajax:
        return jsonify({'ok': True})

    flash('Eliminado.', 'info')
    return redirect(url_for('egresado.editar_perfil'))


# ============================================
# Ofertas Laborales
# ============================================

@egresado.route('/ofertas')
@login_required
@solo_egresado
def ofertas():
    # Se conserva la navegación dentro del área autenticada del egresado.
    buscar = request.args.get('q', '').strip()[:100]
    ubicacion = request.args.get('ubicacion', '').strip()[:80]
    pagina = max(1, request.args.get('pagina', 1, type=int))
    q = OfertasLaborales.query.filter(
        OfertasLaborales.activa == 1,
        OfertasLaborales.fecha_vencimiento >= date.today()
    )
    if buscar:
        patron = f'%{buscar}%'
        q = q.filter(or_(OfertasLaborales.titulo.ilike(patron),
                         OfertasLaborales.descripcion.ilike(patron),
                         OfertasLaborales.requisitos.ilike(patron),
                         OfertasLaborales.empresa.ilike(patron)))
    if ubicacion:
        q = q.filter(OfertasLaborales.ubicacion.ilike(f'%{ubicacion}%'))
    paginacion = q.order_by(OfertasLaborales.fecha_publicacion.desc(),
                            OfertasLaborales.id_oferta.desc()).paginate(
                                page=pagina, per_page=9, error_out=False)
    migracion_v8 = tablas_v8_disponibles()
    guardadas = (OfertasGuardadas.query.filter_by(id_egresado=current_user.id_egresado).all()
                if migracion_v8 else [])
    postuladas = (Postulaciones.query.filter_by(id_egresado=current_user.id_egresado).all()
                 if migracion_v8 else [])
    mis_documentos = DocumentosEgresado.query.filter_by(id_egresado=current_user.id_egresado)\
        .order_by(DocumentosEgresado.es_cv_principal.desc(), DocumentosEgresado.creado_en.desc()).all()
    token = session.get('nexo_ofertas_csrf')
    if not token:
        token = secrets.token_urlsafe(32)
        session['nexo_ofertas_csrf'] = token
    return render_template('egresado/ofertas.html',
        ofertas=paginacion.items, paginacion=paginacion,
        buscar=buscar, ubicacion=ubicacion, csrf_ofertas=token,
        migracion_v8=migracion_v8,
        mis_documentos=mis_documentos,
        ids_guardadas={i.id_oferta for i in guardadas},
        ids_postuladas={i.id_oferta for i in postuladas},
        guardados_total=len(guardadas), postulaciones_total=len(postuladas),
        programa_actual=(current_user.egresado.curricula.programa.nombre
            if current_user.egresado and current_user.egresado.curricula else None))


def _comprobar_csrf_ofertas():
    enviado = request.form.get('_csrf', '')
    esperado = session.get('nexo_ofertas_csrf', '')
    if not esperado or not hmac.compare_digest(esperado, enviado):
        abort(400, 'Formulario expirado. Actualiza la página y vuelve a intentarlo.')


@egresado.route('/ofertas/<int:id_oferta>/guardar', methods=['POST'])
@login_required
@solo_egresado
def guardar_oferta(id_oferta):
    _comprobar_csrf_ofertas()
    if not tablas_v8_disponibles():
        flash('La función Guardar requiere aplicar primero la migración SQL V8.', 'warning')
        return redirect(url_for('egresado.ofertas'))
    oferta = OfertasLaborales.query.get_or_404(id_oferta)
    if not oferta.activa or oferta.fecha_vencimiento < date.today():
        flash('La oferta ya no está disponible.', 'warning')
    else:
        actual = OfertasGuardadas.query.filter_by(
            id_egresado=current_user.id_egresado, id_oferta=oferta.id_oferta).first()
        if actual:
            db.session.delete(actual)
            flash('Oferta retirada de guardados.', 'info')
        else:
            db.session.add(OfertasGuardadas(id_egresado=current_user.id_egresado, id_oferta=oferta.id_oferta))
            flash('Oferta guardada en tu perfil.', 'success')
        db.session.commit()
    return redirect(url_for('egresado.ofertas'))


@egresado.route('/ofertas/<int:id_oferta>/postular', methods=['POST'])
@login_required
@solo_egresado
def postular_oferta(id_oferta):
    _comprobar_csrf_ofertas()
    if not tablas_v8_disponibles():
        flash('La postulación interna requiere la migración SQL V8.', 'warning')
        return redirect(url_for('egresado.ofertas'))
    oferta = OfertasLaborales.query.get_or_404(id_oferta)
    if oferta.url_original:
        flash('Esta oferta utiliza postulación externa: completa el proceso en el portal original.', 'info')
        return redirect(url_for('egresado.ofertas'))
    if not oferta.activa or oferta.fecha_vencimiento < date.today():
        flash('La oferta ya no acepta postulaciones.', 'warning')
        return redirect(url_for('egresado.ofertas'))
    actual = Postulaciones.query.filter_by(
        id_egresado=current_user.id_egresado, id_oferta=id_oferta).first()
    if actual:
        flash('Ya registraste tu postulación a esta oferta.', 'info')
    else:
        ids_docs = request.form.getlist('documentos_autorizados')
        docs_validos = (
            DocumentosEgresado.query.filter(
                DocumentosEgresado.id_egresado == current_user.id_egresado,
                DocumentosEgresado.id_documento.in_(ids_docs)
            ).all() if ids_docs else []
        )
        cv_doc = next((d for d in docs_validos if d.categoria == 'cv'), None)

        post = Postulaciones(
            id_egresado=current_user.id_egresado,
            id_oferta=id_oferta,
            id_documento_cv=cv_doc.id_documento if cv_doc else None,
            mensaje=request.form.get('mensaje', '').strip()[:1200]
        )
        db.session.add(post)
        db.session.flush()

        for d in docs_validos:
            db.session.add(AutorizacionesDocumentales(
                id_documento=d.id_documento,
                id_egresado=current_user.id_egresado,
                id_empresa=oferta.id_empresa,
                id_postulacion=post.id_postulacion,
                autorizado=1,
            ))

        db.session.commit()
        registrar_auditoria('postular_oferta', 'bolsa_laboral', 'postulaciones', post.id_postulacion)
        flash('Postulación registrada en NEXO UNDAC. Puedes consultar su estado en Mis postulaciones.', 'success')
    return redirect(url_for('egresado.ofertas'))


# ==========================================
# GENERAR CV
# ==========================================

@egresado.route('/mi-cv')
@login_required
@solo_egresado
def seleccionar_cv():
    e              = Egresados.query.get(current_user.id_egresado)
    empleos_l      = Empleos.query.filter_by(id_egresado=e.id_egresado)\
                            .order_by(Empleos.fecha_inicio.desc()).all()
    logros_l       = TrayectoriaAcademica.query.filter_by(id_egresado=e.id_egresado)\
                                            .order_by(TrayectoriaAcademica.fecha_obtencion.desc()).all()
    certificados_l = Certificados.query.filter_by(id_egresado=e.id_egresado)\
                                     .order_by(Certificados.fecha_emision.desc()).all()
    return render_template('egresado/seleccionar_cv.html',
        e=e, empleos=empleos_l, logros=logros_l, certificados=certificados_l)


@egresado.route('/mi-cv/generar', methods=['POST'])
@login_required
@solo_egresado
def generar_cv_final():
    from app.utils.cv_pdf import generar_cv
    e = Egresados.query.get(current_user.id_egresado)

    e.titulo_cv          = request.form.get('titulo_cv', '').strip() or None
    e.perfil_profesional = request.form.get('perfil_profesional', '').strip() or None
    db.session.commit()

    ids_empleos      = request.form.getlist('empleos')
    ids_logros       = request.form.getlist('logros')
    ids_certificados = request.form.getlist('certificados')

    empleos_sel      = Empleos.query.filter(Empleos.id_egresado == e.id_egresado, Empleos.id_empleo.in_(ids_empleos)).all() if ids_empleos else []
    logros_sel       = TrayectoriaAcademica.query.filter(TrayectoriaAcademica.id_egresado == e.id_egresado, TrayectoriaAcademica.id_trayectoria.in_(ids_logros)).all() if ids_logros else []
    certificados_sel = Certificados.query.filter(Certificados.id_egresado == e.id_egresado, Certificados.id_certificado.in_(ids_certificados)).all() if ids_certificados else []

    habilidades_l = Habilidades.query.filter_by(id_egresado=e.id_egresado, tipo='habilidad').all()
    intereses_l   = Habilidades.query.filter_by(id_egresado=e.id_egresado, tipo='interes').all()
    idiomas_l     = Certificados.query.filter_by(id_egresado=e.id_egresado, categoria='idioma').all()

    pdf = generar_cv(e, empleos_sel, logros_sel, certificados_sel, habilidades_l, intereses_l, idiomas_l)
    nombre_archivo = f"CV_{e.apellido_paterno}_{e.nombres.split()[0]}.pdf"
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=nombre_archivo)


# =====================================
# ENCUESTAS
# =====================================
from app.models import Encuesta, Preguntas, Opciones, Respuestas

@egresado.route('/encuestas')
@login_required
@solo_egresado
def encuesta():
    e = Egresados.query.get(current_user.id_egresado)

    respondidas_ids = {r[0] for r in db.session.query(Respuestas.id_encuesta)
                        .filter_by(id_egresado=e.id_egresado).distinct().all()}

    q = Encuesta.query.filter_by(estado='publicada')
    if respondidas_ids:
        q = q.filter(~Encuesta.id_encuesta.in_(respondidas_ids))

    pendientes = q.order_by(Encuesta.anio.desc()).all()
    return render_template('egresado/encuesta.html', encuestas=pendientes)


@egresado.route('/encuestas/<int:id>', methods=['GET', 'POST'])
@login_required
@solo_egresado
def responder_encuesta(id):
    enc = Encuesta.query.get_or_404(id)
    e   = Egresados.query.get(current_user.id_egresado)

    if (enc.estado != 'publicada' or
        (enc.fecha_inicio and date.today() < enc.fecha_inicio) or
        (enc.fecha_fin and date.today() > enc.fecha_fin)):
        flash('Esta encuesta no está disponible en la fecha actual.', 'warning')
        return redirect(url_for('egresado.encuesta'))

    ya_respondida = Respuestas.query.filter_by(id_encuesta=id, id_egresado=e.id_egresado).first()
    if ya_respondida:
        flash('Ya respondiste esta encuesta. ¡Gracias!', 'info')
        return redirect(url_for('egresado.encuesta'))

    preguntas = Preguntas.query.filter_by(id_encuesta=id).order_by(Preguntas.orden).all()

    if request.method == 'POST':
        respuestas_a_guardar = []

        for p in preguntas:
            campo = f'pregunta_{p.id_pregunta}'

            if p.tipo == 'opcion_multiple':
                valores = request.form.getlist(campo)
                if p.obligatoria and not valores:
                    flash(f'La pregunta "{p.texto}" es obligatoria.', 'danger')
                    return render_template('egresado/responder_encuesta.html', encuesta=enc, preguntas=preguntas)
                opciones_validas = {str(op.id_opcion) for op in p.opciones}
                if len(valores) != len(set(valores)) or any(v not in opciones_validas for v in valores):
                    abort(400, 'Se ha enviado una opción que no corresponde a la pregunta.')
                for v in valores:
                    respuestas_a_guardar.append(Respuestas(
                        id_encuesta=id, id_egresado=e.id_egresado,
                        id_pregunta=p.id_pregunta, id_opcion=int(v)
                    ))
                continue

            valor = request.form.get(campo, '').strip() if p.tipo in ('texto', 'numero') else request.form.get(campo)

            if p.obligatoria and not valor:
                flash(f'La pregunta "{p.texto}" es obligatoria.', 'danger')
                return render_template('egresado/responder_encuesta.html', encuesta=enc, preguntas=preguntas)

            if not valor:
                continue  # pregunta opcional sin responder

            resp = Respuestas(id_encuesta=id, id_egresado=e.id_egresado, id_pregunta=p.id_pregunta)

            if p.tipo == 'texto':
                resp.respuesta_texto = valor[:3000]
            elif p.tipo == 'numero':
                try:
                    numero = Decimal(str(valor))
                    if not numero.is_finite() or abs(numero) > Decimal('99999999.99'):
                        raise ValueError('Fuera del límite permitido')
                    resp.respuesta_numero = numero
                except (InvalidOperation, ValueError):
                    flash('Revisa el valor numérico de la encuesta.', 'danger')
                    return render_template('egresado/responder_encuesta.html', encuesta=enc, preguntas=preguntas)
            elif p.tipo == 'si_no':
                if valor not in ('si','no'):
                    abort(400, 'Respuesta de sí/no inválida.')
                resp.respuesta_booleana = 1 if valor == 'si' else 0
            elif p.tipo == 'opcion_unica':
                if str(valor) not in {str(op.id_opcion) for op in p.opciones}:
                    abort(400, 'Opción no válida para esta pregunta.')
                resp.id_opcion = int(valor)

            respuestas_a_guardar.append(resp)

        if not respuestas_a_guardar:
            flash('Responde al menos una pregunta antes de enviar la encuesta.', 'warning')
            return render_template('egresado/responder_encuesta.html', encuesta=enc, preguntas=preguntas)
        db.session.add_all(respuestas_a_guardar)
        db.session.commit()
        flash('¡Gracias por responder la encuesta! Tu opinión es muy importante.', 'success')
        return redirect(url_for('egresado.encuesta'))

    return render_template('egresado/responder_encuesta.html', encuesta=enc, preguntas=preguntas)