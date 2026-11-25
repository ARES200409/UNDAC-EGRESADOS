# app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth
from app.auth.forms import (
    LoginForm, VerificarForm, CompletarRegistroForm,
    CambiarContrasenaForm, RegistroEmpresaForm
)
from app.extensions import db, bcrypt, mail
from app.models import Usuarios, Egresados, Roles, UsuarioRoles, Personal, Empresas, Sectores
from app.helpers import consultar_api, datos_api_a_egresado, resolver_curricula
from app.ambito import validar_programa_api, es_egresado_en_ambito
from app.services.auditoria_service import registrar_auditoria
from app.services.validaciones_service import validar_ruc_peru
from datetime import datetime, timedelta, date, timezone
from flask_mail import Message
import secrets


def url_destino_rol(id_rol):
    """Decide a dónde redirigir según el rol con el que se inició sesión."""
    rol = db.session.get(Roles, id_rol) if id_rol else None
    if rol and rol.nombre == 'egresado':
        return url_for('egresado.perfil')
    if rol and rol.nombre == 'empresa':
        return url_for('empresa.panel')
    if rol:
        return url_for('admin.dashboard')
    # Fallback por si se perdió el dato de sesión
    if current_user.is_authenticated and current_user.es_egresado():
        return url_for('egresado.perfil')
    if current_user.is_authenticated and current_user.es_empresa():
        return url_for('empresa.panel')
    return url_for('auth.login')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_destino_rol(session.get('rol_activo')))

    form = LoginForm()
    # Cargar todos los roles existentes como opciones (egresado primero, por defecto)
    todos_roles = Roles.query.order_by(
        db.case((Roles.nombre == 'egresado', 0), else_=1), Roles.nombre
    ).all()
    form.rol.choices = [(str(r.id_rol), r.nombre.replace('_', ' ').title()) for r in todos_roles]

    if form.validate_on_submit():
        correo_ingresado = (form.correo.data or '').strip().lower()
        usuario = Usuarios.query.filter_by(correo=correo_ingresado).first()
        ahora = datetime.now(timezone.utc).replace(tzinfo=None)

        if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
            segundos = int((usuario.bloqueado_hasta - ahora).total_seconds())
            minutos = max(1, (segundos + 59) // 60)
            registrar_auditoria(
                'login_bloqueado', 'auth', 'usuarios', usuario.id_usuario,
                resultado='denegado', detalle='Intento de acceso mientras cuenta está bloqueada',
                id_usuario=usuario.id_usuario
            )
            flash(f'Cuenta bloqueada temporalmente por intentos fallidos. Intenta nuevamente en {minutos} minuto(s).', 'danger')
            return render_template('auth/login.html', form=form)

        if usuario and bcrypt.check_password_hash(usuario.contrasena_hash, form.contrasena.data):

            if usuario.estado != 'activo':
                registrar_auditoria('login_inactivo', 'auth', 'usuarios', usuario.id_usuario, resultado='denegado', id_usuario=usuario.id_usuario)
                flash('Cuenta desactivada. Contacta al administrador.', 'warning')
                return render_template('auth/login.html', form=form)

            if usuario.id_egresado and not es_egresado_en_ambito(usuario.egresado):
                registrar_auditoria('login_fuera_ambito', 'auth', 'usuarios', usuario.id_usuario, resultado='denegado', id_usuario=usuario.id_usuario)
                flash('La cuenta no pertenece al programa habilitado para este sistema.', 'warning')
                return render_template('auth/login.html', form=form)

            if usuario.id_personal:
                persona = db.session.get(Personal, usuario.id_personal)
                if persona and persona.estado != 'activo':
                    registrar_auditoria('login_personal_inactivo', 'auth', 'personal', persona.id_personal, resultado='denegado', id_usuario=usuario.id_usuario)
                    flash('Tu cuenta ha sido desactivada. Contacta al administrador.', 'danger')
                    return render_template('auth/login.html', form=form)

            if usuario.id_empresa:
                empresa = db.session.get(Empresas, usuario.id_empresa)
                if not empresa or empresa.estado != 'activa':
                    registrar_auditoria('login_empresa_pendiente', 'auth', 'empresas', usuario.id_empresa, resultado='denegado', id_usuario=usuario.id_usuario)
                    flash('Tu cuenta empresarial aún está pendiente de validación por el administrador.', 'warning')
                    return render_template('auth/login.html', form=form)

            id_rol_elegido = int(form.rol.data)
            ids_del_usuario = [r.id_rol for r in usuario.roles]

            if id_rol_elegido not in ids_del_usuario:
                registrar_auditoria('login_rol_invalido', 'auth', 'usuarios', usuario.id_usuario, resultado='denegado', detalle=f'Rol {id_rol_elegido} no asignado', id_usuario=usuario.id_usuario)
                flash('Tu cuenta no tiene ese rol asignado.', 'warning')
                return render_template('auth/login.html', form=form)

            login_user(usuario)
            session['rol_activo'] = id_rol_elegido
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.ultimo_acceso = ahora
            db.session.commit()
            registrar_auditoria('login_exito', 'auth', 'usuarios', usuario.id_usuario, resultado='exito', detalle=f'Rol ID {id_rol_elegido}', id_usuario=usuario.id_usuario)

            return redirect(url_destino_rol(id_rol_elegido))

        if usuario:
            max_intentos = int(current_app.config.get('LOGIN_MAX_ATTEMPTS', 5))
            lock_secs = int(current_app.config.get('LOGIN_LOCKOUT_SECONDS', 300))
            usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
            if usuario.intentos_fallidos >= max_intentos:
                usuario.bloqueado_hasta = ahora + timedelta(seconds=lock_secs)
                usuario.intentos_fallidos = 0
                db.session.commit()
                registrar_auditoria('login_bloqueo_activado', 'auth', 'usuarios', usuario.id_usuario, resultado='denegado', detalle='Superó límite de intentos fallidos', id_usuario=usuario.id_usuario)
                flash('Demasiados intentos fallidos. Tu cuenta fue bloqueada temporalmente por seguridad.', 'danger')
                return render_template('auth/login.html', form=form)
            db.session.commit()
            registrar_auditoria('login_fallido', 'auth', 'usuarios', usuario.id_usuario, resultado='denegado', detalle='Contraseña incorrecta', id_usuario=usuario.id_usuario)
        else:
            registrar_auditoria('login_fallido', 'auth', 'usuarios', None, resultado='denegado', detalle='Correo no registrado')

        flash('Correo o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html', form=form)


@auth.route('/verificar', methods=['GET', 'POST'])
def verificar():
    """Paso 1: verifica código universitario y DNI con el API."""
    if current_user.is_authenticated:
        return redirect(url_destino_rol(session.get('rol_activo')))

    form = VerificarForm()
    datos_encontrados = None

    if form.validate_on_submit():
        datos = consultar_api(form.codigo_universitario.data)

        if not datos:
            flash('Código universitario no encontrado o no pertenece a Sistemas y Computación.', 'danger')

        elif not validar_programa_api(datos):
            flash('Esta plataforma está habilitada para egresados de Ingeniería de Sistemas y Computación.', 'warning')

        elif str(datos.get('Dni') or '').strip() != str(form.dni.data or '').strip():
            flash('El DNI no coincide con el código universitario ingresado.', 'danger')

        elif datos.get('Rol') != 'EG':
            flash('Solo pueden registrarse egresados. Tu estado actual es: ' + datos.get('Rol', '?'), 'warning')

        elif Egresados.query.filter_by(codigo_universitario=form.codigo_universitario.data).first():
            flash('Este código universitario ya tiene una cuenta. Inicia sesión.', 'warning')
            return redirect(url_for('auth.login'))

        else:
            session['reg_codigo'] = form.codigo_universitario.data
            session['reg_dni']    = form.dni.data
            datos_encontrados = datos

    return render_template('auth/verificar.html', form=form, datos=datos_encontrados)


@auth.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_destino_rol(session.get('rol_activo')))

    if 'reg_codigo' not in session:
        flash('Primero debes verificar tu código universitario.', 'warning')
        return redirect(url_for('auth.verificar'))

    form = CompletarRegistroForm()
    if form.validate_on_submit():
        codigo = session.get('reg_codigo')

        datos = consultar_api(codigo)
        if not datos:
            flash('Error al obtener datos. Intenta de nuevo.', 'danger')
            return redirect(url_for('auth.verificar'))

        if (not validar_programa_api(datos) or datos.get('Rol') != 'EG'
                or str(datos.get('Dni') or '').strip() != str(session.get('reg_dni') or '').strip()):
            session.pop('reg_codigo', None)
            session.pop('reg_dni', None)
            flash('La verificación académica debe realizarse nuevamente.', 'warning')
            return redirect(url_for('auth.verificar'))

        curricula = resolver_curricula(
            datos.get('Curricula'),
            datos.get('Fecha de Ingreso'),
            datos.get('Programa facultad'),
            datos.get('ID_ESCUELA')
        )
        if not curricula:
            flash('Tu identidad fue verificada, pero el plan académico informado por la UNDAC aún no está registrado en el catálogo del sistema. Solicita al administrador configurar la currícula correspondiente.', 'warning')
            return redirect(url_for('auth.verificar'))

        campos = datos_api_a_egresado(datos)
        campos['codigo_universitario'] = codigo
        campos['id_curricula']         = curricula.id_curricula

        egresado = Egresados.query.filter_by(dni=datos.get('Dni')).first()

        if egresado:
            for key, value in campos.items():
                setattr(egresado, key, value)
        else:
            egresado = Egresados(**campos)
            db.session.add(egresado)

        db.session.flush()

        correo_login = request.form.get('correo', '').strip() or datos.get('Correo Institucional')

        if Usuarios.query.filter_by(correo=correo_login).first():
            flash('Ese correo ya tiene una cuenta registrada.', 'warning')
            return render_template('auth/registro.html', form=form,
                                    correo_api=datos.get('Correo Institucional'))

        hash_clave = bcrypt.generate_password_hash(form.contrasena.data).decode('utf-8')

        usuario = Usuarios(
            correo=correo_login,
            contrasena_hash=hash_clave,
            id_egresado=egresado.id_egresado
        )
        db.session.add(usuario)
        db.session.flush()

        rol_egresado = Roles.query.filter_by(nombre='egresado').first()
        db.session.add(UsuarioRoles(id_usuario=usuario.id_usuario, id_rol=rol_egresado.id_rol))

        egresado.correo_institucional = correo_login
        db.session.commit()

        session.pop('reg_codigo', None)
        session.pop('reg_dni', None)

        flash('Cuenta creada. Inicia sesión con tu correo institucional.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    uid = current_user.id_usuario
    logout_user()
    session.pop('rol_activo', None)
    registrar_auditoria('logout', 'auth', 'usuarios', uid, resultado='exito', id_usuario=uid)
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/registro-empresa', methods=['GET', 'POST'])
def registro_empresa():
    """Registro público para empleadores/empresas (sujeto a validación del administrador)."""
    if current_user.is_authenticated:
        return redirect(url_destino_rol(session.get('rol_activo')))

    form = RegistroEmpresaForm()
    sectores = Sectores.query.order_by(Sectores.nombre).all()
    form.id_sector.choices = [(s.id_sector, s.nombre) for s in sectores]

    if not sectores:
        flash('No hay sectores económicos configurados aún. Contacta al administrador.', 'warning')
        return render_template('auth/registro_empresa.html', form=form)

    if form.validate_on_submit():
        ruc = form.ruc.data.strip()
        correo = form.correo.data.strip().lower()

        if not validar_ruc_peru(ruc):
            flash('Ingresa un RUC peruano válido de 11 dígitos (inicia con 10, 15, 17 o 20).', 'warning')
            return render_template('auth/registro_empresa.html', form=form)

        if Empresas.query.filter_by(ruc=ruc).first():
            flash('Ya existe una empresa registrada con ese RUC.', 'warning')
            return render_template('auth/registro_empresa.html', form=form)

        if Usuarios.query.filter_by(correo=correo).first():
            flash('Ese correo electrónico ya está registrado en el sistema.', 'warning')
            return render_template('auth/registro_empresa.html', form=form)

        empresa = Empresas(
            ruc=ruc,
            razon_social=form.razon_social.data.strip(),
            nombre_comercial=(form.nombre_comercial.data or '').strip() or None,
            id_sector=form.id_sector.data,
            direccion=(form.direccion.data or '').strip() or None,
            telefono=(form.telefono.data or '').strip() or None,
            sitio_web=(form.sitio_web.data or '').strip() or None,
            pais='Perú',
            estado='pendiente',
        )
        db.session.add(empresa)
        db.session.flush()

        hash_clave = bcrypt.generate_password_hash(form.contrasena.data).decode('utf-8')
        usuario = Usuarios(
            correo=correo,
            contrasena_hash=hash_clave,
            id_empresa=empresa.id_empresa,
            estado='activo',
        )
        db.session.add(usuario)
        db.session.flush()

        rol_emp = Roles.query.filter_by(nombre='empresa').first()
        if rol_emp:
            db.session.add(UsuarioRoles(id_usuario=usuario.id_usuario, id_rol=rol_emp.id_rol))

        db.session.commit()
        registrar_auditoria(
            'registro_empresa', 'auth', 'empresas', empresa.id_empresa,
            resultado='exito', detalle=f'RUC {ruc} pendiente de validación',
            id_usuario=usuario.id_usuario
        )
        flash('Solicitud enviada. Un administrador validará tu empresa antes de tu primer ingreso.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro_empresa.html', form=form)


@auth.route('/cambiar-contrasena', methods=['GET', 'POST'])
@login_required
def cambiar_contrasena():
    form = CambiarContrasenaForm()
    if form.validate_on_submit():

        if not bcrypt.check_password_hash(current_user.contrasena_hash, form.contrasena_actual.data):
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('auth/cambiar_contrasena.html', form=form)

        current_user.contrasena_hash = bcrypt.generate_password_hash(form.nueva.data).decode('utf-8')
        db.session.commit()
        flash('Contraseña actualizada correctamente.', 'success')
        return redirect(url_destino_rol(session.get('rol_activo')))

    return render_template('auth/cambiar_contrasena.html', form=form)


# ==============================================
# RECUPERACIÓN DE CONTRASEÑA
# ==============================================
@auth.route('/recuperar-contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))

    if request.method == 'POST':
        correo  = request.form.get('correo', '').strip()
        usuario = Usuarios.query.filter_by(correo=correo).first()

        flash('Si ese correo está registrado, recibirás un enlace en breve.', 'info')

        if usuario:
            token     = secrets.token_urlsafe(32)
            expira_en = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)

            usuario.token_recuperacion = token
            usuario.token_expiracion   = expira_en
            db.session.commit()

            enlace = url_for('auth.restablecer_contrasena', token=token, _external=True)
            msg = Message(
                subject='Recuperación de contraseña — Egresados UNDAC',
                recipients=[correo]
            )
            msg.html = f'''
            <div style="font-family:Segoe UI,sans-serif;max-width:480px;margin:0 auto;">
                <div style="background:#003876;padding:24px;text-align:center;border-radius:12px 12px 0 0;">
                    <h2 style="color:#fff;margin:0;font-size:1.2rem;">Sistema de Egresados UNDAC</h2>
                    <p style="color:rgba(255,255,255,.75);margin:6px 0 0;font-size:.85rem;">
                        Escuela de Sistemas y Computación
                    </p>
                </div>
                <div style="background:#fff;padding:28px;border:1px solid #e5e7eb;border-radius:0 0 12px 12px;">
                    <p style="color:#374151;">Recibimos una solicitud para restablecer tu contraseña.</p>
                    <p style="color:#374151;">Haz clic en el botón para crear una nueva:</p>
                    <div style="text-align:center;margin:24px 0;">
                        <a href="{enlace}" style="background:#003876;color:#fff;padding:12px 28px;
                           border-radius:8px;text-decoration:none;font-weight:700;">
                            Restablecer contraseña
                        </a>
                    </div>
                    <p style="color:#6b7280;font-size:.82rem;">
                        Este enlace expira en <strong>30 minutos</strong>.<br>
                        Si no solicitaste esto, ignora este correo.
                    </p>
                </div>
            </div>
            '''
            try:
                mail.send(msg)
            except Exception:
                pass

        return redirect(url_for('auth.login'))

    return render_template('auth/recuperar_contrasena.html')


@auth.route('/restablecer-contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))

    usuario = Usuarios.query.filter_by(token_recuperacion=token).first()

    if not usuario or not usuario.token_expiracion or usuario.token_expiracion < datetime.now(timezone.utc).replace(tzinfo=None):
        flash('El enlace no es válido o ya expiró. Solicita uno nuevo.', 'danger')
        return redirect(url_for('auth.recuperar_contrasena'))

    if request.method == 'POST':
        nueva     = request.form.get('contrasena', '').strip()
        confirmar = request.form.get('confirmar', '').strip()

        if len(nueva) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'warning')
            return render_template('auth/restablecer_contrasena.html', token=token)

        if nueva != confirmar:
            flash('Las contraseñas no coinciden.', 'warning')
            return render_template('auth/restablecer_contrasena.html', token=token)

        usuario.contrasena_hash    = bcrypt.generate_password_hash(nueva).decode('utf-8')
        usuario.token_recuperacion = None
        usuario.token_expiracion   = None
        db.session.commit()

        flash('Contraseña actualizada correctamente. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/restablecer_contrasena.html', token=token)