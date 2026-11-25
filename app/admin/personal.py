# app/admin/personal.py
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.admin import admin
from app.admin.helpers import (requiere_rol, _facultades_de_coordinador,
                                _ids_personal_gestionado_por_coordinador,
                                _coordinador_gestiona_a)
from app.extensions import db, bcrypt
from app.models import Personal, Usuarios, Roles, UsuarioRoles, AsignacionesPersonal, Facultades, ProgramasEstudio
from datetime import date
from app.ambito import ids_programa_sistemas, ids_facultad_sistemas


@admin.route('/admin/personal')
@login_required
@requiere_rol('administrador')
def personal():
    rol_activo = current_user.rol_activo_nombre()

    if rol_activo in ('administrador', 'utsag'):
        q = db.session.query(Personal, Usuarios).join(Usuarios, Usuarios.id_personal == Personal.id_personal)
        if rol_activo == 'utsag':
            q = q.filter(Personal.id_personal != 1)
        lista = q.order_by(Personal.apellido_paterno).all()
    else:  # coordinador
        ids_gestionados = _ids_personal_gestionado_por_coordinador(current_user.id_personal)
        lista = db.session.query(Personal, Usuarios)\
                          .join(Usuarios, Usuarios.id_personal == Personal.id_personal)\
                          .filter(Personal.id_personal.in_(ids_gestionados))\
                          .order_by(Personal.apellido_paterno).all() if ids_gestionados else []

    ids_prog = set(ids_programa_sistemas() or [])
    ids_fac = set(ids_facultad_sistemas() or [])
    fuera_ambito = {}
    asignados_sistemas = {}
    for persona, usuario in lista:
        activos = [a for a in persona.asignaciones if a.estado == 'activo']
        fuera_ambito[persona.id_personal] = any(
            (a.id_facultad is not None and a.id_facultad not in ids_fac) or
            (a.id_programa is not None and a.id_programa not in ids_prog)
            for a in activos
        )
        asignados_sistemas[persona.id_personal] = any(
            (a.id_facultad is not None and a.id_facultad in ids_fac) or
            (a.id_programa is not None and a.id_programa in ids_prog)
            for a in activos
        )
    return render_template('admin/personal.html', lista=lista, rol_activo=rol_activo,
                           fuera_ambito=fuera_ambito, asignados_sistemas=asignados_sistemas,
                           ids_fac_sistemas=ids_fac, ids_prog_sistemas=ids_prog,
                           catalogo_sistemas_preparado=bool(ids_prog))


@admin.route('/admin/personal/nuevo', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador')
def nuevo_personal():
    rol_activo = current_user.rol_activo_nombre()

    if rol_activo in ('administrador', 'utsag'):
        permitidos = (['administrador', 'utsag', 'coordinador', 'docente_responsable']
                     if rol_activo == 'administrador' else ['coordinador', 'docente_responsable'])
        roles_disponibles = Roles.query.filter(Roles.nombre.in_(permitidos)).order_by(Roles.id_rol).all()
        alcance = ids_programa_sistemas()
        programas_q = ProgramasEstudio.query
        if alcance is not None:
            programas_q = programas_q.filter(ProgramasEstudio.id_programa.in_(alcance))
        programas_disponibles = programas_q.order_by(ProgramasEstudio.nombre).all()
        ids_facultades = {p.id_facultad for p in programas_disponibles}
        facultades_disponibles = Facultades.query.filter(
            Facultades.id_facultad.in_(ids_facultades)).order_by(Facultades.nombre).all()
    else:  # coordinador
        roles_disponibles = Roles.query.filter_by(nombre='docente_responsable').all()
        facultades_disponibles = []
        ids_facultades_propias = _facultades_de_coordinador(current_user.id_personal)
        programas_disponibles = ProgramasEstudio.query.filter(
            ProgramasEstudio.id_facultad.in_(ids_facultades_propias)
        ).order_by(ProgramasEstudio.nombre).all() if ids_facultades_propias else []

        if not programas_disponibles:
            flash('No tienes facultades asignadas todavía, no puedes crear personal.', 'warning')
            return redirect(url_for('admin.personal'))

    if request.method == 'POST':
        correo     = request.form.get('correo', '').strip()
        contrasena = request.form.get('contrasena', '').strip()
        ids_roles  = request.form.getlist('roles')
        ids_permitidos = {str(r.id_rol) for r in roles_disponibles}

        if Usuarios.query.filter_by(correo=correo).first():
            flash('Ese correo ya está registrado.', 'warning')
            return redirect(url_for('admin.nuevo_personal'))

        if len(contrasena) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'warning')
            return redirect(url_for('admin.nuevo_personal'))

        if not ids_roles or not set(ids_roles).issubset(ids_permitidos):
            flash('Selección de roles inválida.', 'danger')
            return redirect(url_for('admin.nuevo_personal'))

        rol_coord   = Roles.query.filter_by(nombre='coordinador').first()
        rol_docente = Roles.query.filter_by(nombre='docente_responsable').first()
        ids_facultades = request.form.getlist('facultades')
        ids_programas  = request.form.getlist('programas')

        ids_fac_validos = {str(f.id_facultad) for f in facultades_disponibles}
        ids_prog_validos = {str(p.id_programa) for p in programas_disponibles}
        if not set(ids_facultades).issubset(ids_fac_validos) or not set(ids_programas).issubset(ids_prog_validos):
            flash('Asignación académica no permitida.', 'danger')
            return redirect(url_for('admin.nuevo_personal'))

        if rol_coord and str(rol_coord.id_rol) in ids_roles and not ids_facultades:
            flash('Selecciona al menos una facultad para el coordinador.', 'warning')
            return redirect(url_for('admin.nuevo_personal'))

        if rol_docente and str(rol_docente.id_rol) in ids_roles:
            if not ids_programas:
                flash('Selecciona al menos un programa para el docente responsable.', 'warning')
                return redirect(url_for('admin.nuevo_personal'))
            # El conjunto de programas ya se validó contra el alcance permitido.
            pass

        if not correo or not request.form.get('nombres','').strip() or not request.form.get('apellido_paterno','').strip():
            flash('Completa nombres, apellido paterno y correo.', 'danger')
            return redirect(url_for('admin.nuevo_personal'))

        nuevo = Personal(
            nombres          = request.form.get('nombres', '').strip(),
            apellido_paterno = request.form.get('apellido_paterno', '').strip(),
            apellido_materno = request.form.get('apellido_materno', '').strip() or None,
            telefono         = request.form.get('telefono', '').strip() or None,
            estado           = 'activo'
        )
        db.session.add(nuevo)
        db.session.flush()

        hash_clave = bcrypt.generate_password_hash(contrasena).decode('utf-8')
        usuario = Usuarios(correo=correo, contrasena_hash=hash_clave, id_personal=nuevo.id_personal)
        db.session.add(usuario)
        db.session.flush()

        for rid in ids_roles:
            db.session.add(UsuarioRoles(id_usuario=usuario.id_usuario, id_rol=int(rid)))

        if rol_coord and str(rol_coord.id_rol) in ids_roles:
            for idf in ids_facultades:
                db.session.add(AsignacionesPersonal(
                    id_personal=nuevo.id_personal, id_rol=rol_coord.id_rol,
                    id_facultad=int(idf), fecha_inicio=date.today()))

        if rol_docente and str(rol_docente.id_rol) in ids_roles:
            for idp in ids_programas:
                db.session.add(AsignacionesPersonal(
                    id_personal=nuevo.id_personal, id_rol=rol_docente.id_rol,
                    id_programa=int(idp), fecha_inicio=date.today()))

        db.session.commit()
        flash('Cuenta de personal creada correctamente.', 'success')
        return redirect(url_for('admin.personal'))

    return render_template('admin/nuevo_personal.html',
        catalogo_sistemas_preparado=bool(programas_disponibles),
        roles=roles_disponibles, facultades=facultades_disponibles,
        programas=programas_disponibles, rol_activo=rol_activo)


@admin.route('/admin/personal/<int:id>/toggle', methods=['POST'])
@login_required
@requiere_rol('administrador')
def toggle_personal(id):
    persona = Personal.query.get_or_404(id)
    rol_activo = current_user.rol_activo_nombre()

    if persona.id_personal == current_user.id_personal:
        flash('No puedes desactivar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.personal'))

    if persona.id_personal == 1:
        flash('Esta cuenta es la administradora nativa del sistema y no puede desactivarse.', 'danger')
        return redirect(url_for('admin.personal'))

    usuario_objetivo = Usuarios.query.filter_by(id_personal=persona.id_personal).first()
    if usuario_objetivo and usuario_objetivo.tiene_rol('administrador') and rol_activo != 'administrador':
        flash('Solo el administrador puede modificar una cuenta administradora.', 'danger')
        return redirect(url_for('admin.personal'))

    if rol_activo == 'coordinador' and not _coordinador_gestiona_a(current_user.id_personal, persona.id_personal):
        flash('No tienes permiso sobre esa cuenta.', 'danger')
        return redirect(url_for('admin.personal'))

    persona.estado = 'inactivo' if persona.estado == 'activo' else 'activo'
    db.session.commit()
    flash(f'Cuenta {"activada" if persona.estado == "activo" else "desactivada"}.', 'info')
    return redirect(url_for('admin.personal'))


@admin.route('/admin/personal/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador')
def editar_personal(id):
    persona = Personal.query.get_or_404(id)
    usuario = Usuarios.query.filter_by(id_personal=id).first()
    rol_activo = current_user.rol_activo_nombre()

    if rol_activo != 'administrador' and usuario and usuario.tiene_rol('administrador'):
        flash('Solo un administrador puede modificar cuentas administradoras.', 'danger')
        return redirect(url_for('admin.personal'))

    if persona.id_personal == 1 and rol_activo != 'administrador':
        flash('Esta cuenta es la administradora nativa del sistema y no puede editarse.', 'danger')
        return redirect(url_for('admin.personal'))

    if rol_activo == 'coordinador':
        if not _coordinador_gestiona_a(current_user.id_personal, id):
            flash('No tienes permiso sobre esa cuenta.', 'danger')
            return redirect(url_for('admin.personal'))
        roles_disponibles = Roles.query.filter_by(nombre='docente_responsable').all()
        facultades_disponibles = []
        ids_facultades_propias = _facultades_de_coordinador(current_user.id_personal)
        programas_disponibles = ProgramasEstudio.query.filter(
            ProgramasEstudio.id_facultad.in_(ids_facultades_propias)
        ).order_by(ProgramasEstudio.nombre).all() if ids_facultades_propias else []
    else:
        permitidos = (['administrador', 'utsag', 'coordinador', 'docente_responsable']
                     if rol_activo == 'administrador' else ['coordinador', 'docente_responsable'])
        roles_disponibles = Roles.query.filter(Roles.nombre.in_(permitidos)).order_by(Roles.id_rol).all()
        alcance = ids_programa_sistemas()
        programas_q = ProgramasEstudio.query
        if alcance is not None:
            programas_q = programas_q.filter(ProgramasEstudio.id_programa.in_(alcance))
        programas_disponibles = programas_q.order_by(ProgramasEstudio.nombre).all()
        ids_facultades = {p.id_facultad for p in programas_disponibles}
        facultades_disponibles = Facultades.query.filter(
            Facultades.id_facultad.in_(ids_facultades)).order_by(Facultades.nombre).all()

    rol_coord   = Roles.query.filter_by(nombre='coordinador').first()
    rol_docente = Roles.query.filter_by(nombre='docente_responsable').first()

    ids_roles_actuales = {r.id_rol for r in usuario.roles}
    ids_facultades_actuales = {a.id_facultad for a in persona.asignaciones
        if rol_coord and a.id_rol == rol_coord.id_rol and a.id_facultad and a.estado == 'activo'}
    ids_programas_actuales = {a.id_programa for a in persona.asignaciones
        if rol_docente and a.id_rol == rol_docente.id_rol and a.id_programa and a.estado == 'activo'}

    if request.method == 'POST':
        persona.nombres          = request.form.get('nombres', '').strip()
        persona.apellido_paterno = request.form.get('apellido_paterno', '').strip()
        persona.apellido_materno = request.form.get('apellido_materno', '').strip() or None
        persona.telefono         = request.form.get('telefono', '').strip() or None

        ids_roles = request.form.getlist('roles')
        ids_facultades = request.form.getlist('facultades')
        ids_programas = request.form.getlist('programas')
        if rol_activo != 'coordinador':
            permitidos = {str(r.id_rol) for r in roles_disponibles}
            if not ids_roles or not set(ids_roles).issubset(permitidos):
                flash('Selecciona al menos un rol permitido.', 'danger')
                return redirect(url_for('admin.editar_personal', id=id))
            if persona.id_personal == current_user.id_personal and str(Roles.query.filter_by(nombre='administrador').first().id_rol) not in ids_roles and rol_activo == 'administrador':
                flash('No puedes quitarte el rol administrador desde tu propia sesión.', 'danger')
                return redirect(url_for('admin.editar_personal', id=id))
            permitidas_fac = {str(f.id_facultad) for f in facultades_disponibles}
            permitidos_prog = {str(p.id_programa) for p in programas_disponibles}
            if not set(ids_facultades).issubset(permitidas_fac) or not set(ids_programas).issubset(permitidos_prog):
                flash('Asignaciones no autorizadas.', 'danger')
                return redirect(url_for('admin.editar_personal', id=id))
            if rol_coord and str(rol_coord.id_rol) in ids_roles and not ids_facultades:
                flash('El coordinador debe tener una facultad asignada.', 'warning')
                return redirect(url_for('admin.editar_personal', id=id))
            if rol_docente and str(rol_docente.id_rol) in ids_roles and not ids_programas:
                flash('El docente debe tener un programa asignado.', 'warning')
                return redirect(url_for('admin.editar_personal', id=id))
            UsuarioRoles.query.filter_by(id_usuario=usuario.id_usuario).delete()
            for rid in ids_roles:
                db.session.add(UsuarioRoles(id_usuario=usuario.id_usuario, id_rol=int(rid)))
            for rol, ids, campo in ((rol_coord, ids_facultades, 'id_facultad'),
                                     (rol_docente, ids_programas, 'id_programa')):
                if rol:
                    AsignacionesPersonal.query.filter_by(id_personal=id, id_rol=rol.id_rol).delete()
                    if str(rol.id_rol) in ids_roles:
                        for asignado in ids:
                            db.session.add(AsignacionesPersonal(
                                id_personal=id, id_rol=rol.id_rol,
                                **{campo: int(asignado)}, fecha_inicio=date.today()))
        else:
            permitidos_prog = {str(p.id_programa) for p in programas_disponibles}
            if not ids_programas or not set(ids_programas).issubset(permitidos_prog):
                flash('El docente necesita programas de tu facultad.', 'danger')
                return redirect(url_for('admin.editar_personal', id=id))
            if rol_docente:
                AsignacionesPersonal.query.filter_by(id_personal=id, id_rol=rol_docente.id_rol).delete()
                for idp in ids_programas:
                    db.session.add(AsignacionesPersonal(
                        id_personal=id, id_rol=rol_docente.id_rol,
                        id_programa=int(idp), fecha_inicio=date.today()))

        nueva_clave = request.form.get('nueva_contrasena', '').strip()
        if nueva_clave:
            if len(nueva_clave) < 8:
                flash('La nueva contraseña debe tener al menos 8 caracteres.', 'warning')
                return redirect(url_for('admin.editar_personal', id=id))
            usuario.contrasena_hash = bcrypt.generate_password_hash(nueva_clave).decode('utf-8')

        db.session.commit()
        flash('Datos actualizados correctamente.', 'success')
        return redirect(url_for('admin.personal'))

    ids_fac_sistemas = set(ids_facultad_sistemas() or [])
    ids_prog_sistemas = set(ids_programa_sistemas() or [])
    asignaciones_ajenas = [a for a in persona.asignaciones if a.estado == 'activo' and
        ((a.id_facultad is not None and a.id_facultad not in ids_fac_sistemas) or
         (a.id_programa is not None and a.id_programa not in ids_prog_sistemas))]
    return render_template('admin/editar_personal.html',
        asignaciones_ajenas=asignaciones_ajenas,
        catalogo_sistemas_preparado=bool(ids_prog_sistemas),
        persona=persona, usuario=usuario, roles=roles_disponibles, rol_activo=rol_activo,
        facultades=facultades_disponibles, programas=programas_disponibles,
        ids_roles_actuales=ids_roles_actuales,
        ids_facultades_actuales=ids_facultades_actuales,
        ids_programas_actuales=ids_programas_actuales)