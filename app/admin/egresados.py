# app/admin/egresados.py
from flask import render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from app.admin import admin
from app.admin.helpers import requiere_rol, _alcance_programas, _facultades_de_coordinador
from app.extensions import db, bcrypt
from app.models import (
    Egresados, Curriculas, ProgramasEstudio, Facultades,
    Empleos, TrayectoriaAcademica, Certificados, Usuarios, Roles, UsuarioRoles
)
from app.services.auditoria_service import registrar_auditoria
from app.services.validaciones_service import limpiar_texto, entero_en_rango
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
import io


def _celda_excel_segura(valor):
    """Evita que texto del usuario se ejecute como fórmula al abrir el XLSX."""
    if not isinstance(valor, str):
        return valor
    if valor and (valor[0] in ('=', '+', '-', '@', '\t', '\r', '\n') or valor.lstrip().startswith(('=', '+', '-', '@'))):
        return "'" + valor
    return valor

@admin.route('/admin/egresados')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def egresados():
    rol_activo = current_user.rol_activo_nombre()
    alcance    = _alcance_programas(rol_activo, current_user.id_personal)

    # Convertimos a diccionario mutable y removemos 'pagina' si viene en la URL
    filtros = request.args.to_dict()
    filtros.pop('pagina', None)

    q = Egresados.query.join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)

    if alcance is not None:
        q = q.filter(Curriculas.id_programa.in_(alcance)) if alcance else q.filter(db.literal(False))

    id_facultad = request.args.get('id_facultad', type=int)
    id_programa = request.args.get('id_programa', type=int)

    if id_programa:
        q = q.filter(Curriculas.id_programa == id_programa)
    elif id_facultad:
        q = q.join(ProgramasEstudio, Curriculas.id_programa == ProgramasEstudio.id_programa)\
             .filter(ProgramasEstudio.id_facultad == id_facultad)

    buscar        = filtros.get('buscar', '').strip()
    genero        = filtros.get('genero', '')
    curricula     = filtros.get('curricula', '')
    anio_ingreso  = filtros.get('anio_ingreso', '')
    anio_egreso   = filtros.get('anio_egreso', '')
    letra_periodo = filtros.get('letra_periodo', '')
    nivel         = filtros.get('nivel', '')

    if buscar:
        like = f'%{buscar}%'
        q = q.filter(db.or_(
            Egresados.nombres.ilike(like), Egresados.apellido_paterno.ilike(like),
            Egresados.apellido_materno.ilike(like), Egresados.codigo_universitario.ilike(like),
            Egresados.dni.ilike(like), Egresados.telefono.ilike(like),
            Egresados.correo_institucional.ilike(like), Egresados.correo_personal.ilike(like),
        ))
    if genero:        q = q.filter(Egresados.genero == genero)
    if curricula:      q = q.filter(Curriculas.nombre.ilike(f'%{curricula}%'))
    if anio_ingreso and anio_ingreso.isdigit():
        q = q.filter(Egresados.anio_ingreso == int(anio_ingreso))
    if anio_egreso and anio_egreso.isdigit():
        q = q.filter(Egresados.anio_egreso == int(anio_egreso))
    if letra_periodo:  q = q.filter(Egresados.periodo.ilike(f'%{letra_periodo}'))
    if nivel:
        jerarquia = ['egresado', 'bachiller', 'titulado', 'maestria', 'doctorado', 'phd']
        if nivel.startswith('solo_'):
            q = q.filter(Egresados.nivel_maximo == nivel.replace('solo_', ''))
        elif nivel in jerarquia:
            q = q.filter(Egresados.nivel_maximo.in_(jerarquia[jerarquia.index(nivel):]))

    total    = q.count()
    pagina   = request.args.get('pagina', 1, type=int)
    paginado = q.order_by(Egresados.apellido_paterno).paginate(page=pagina, per_page=30, error_out=False)

    q_meta = Egresados.query.join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)
    if alcance is not None:
        q_meta = q_meta.filter(Curriculas.id_programa.in_(alcance))
    egresados_meta = q_meta.all()
    curriculas = sorted({e.curricula.nombre for e in egresados_meta if e.curricula})
    anios_ing = sorted({e.anio_ingreso for e in egresados_meta if e.anio_ingreso})
    anios_eg = sorted({e.anio_egreso for e in egresados_meta if e.anio_egreso})

    if rol_activo in ('administrador', 'utsag'):
        from app.ambito import ids_facultad_sistemas
        facultades_ids = ids_facultad_sistemas()
        facultades = (Facultades.query.order_by(Facultades.nombre).all() if facultades_ids is None
                     else Facultades.query.filter(Facultades.id_facultad.in_(facultades_ids)).order_by(Facultades.nombre).all())
    elif rol_activo == 'coordinador':
        ids_fac = _facultades_de_coordinador(current_user.id_personal)
        facultades = Facultades.query.filter(Facultades.id_facultad.in_(ids_fac)).order_by(Facultades.nombre).all() if ids_fac else []
    else:
        facultades = []

    programas_q = ProgramasEstudio.query.filter_by(id_facultad=id_facultad)
    if alcance is not None:
        programas_q = programas_q.filter(ProgramasEstudio.id_programa.in_(alcance))
    programas = programas_q.order_by(ProgramasEstudio.nombre).all() if id_facultad else []

    plantilla = ('admin/_v11_resultados_egresados.html'
                if request.headers.get('HX-Request') == 'true' else 'admin/egresados.html')
    return render_template(plantilla,
        egresados=paginado.items, total=total, hay_filtro=True, paginacion=paginado,
        curriculas=curriculas, anios_ing=anios_ing, anios_eg=anios_eg,
        filtros=filtros, rol_activo=rol_activo,
        facultades=facultades, programas=programas,
        id_facultad=id_facultad, id_programa=id_programa)


@admin.route('/admin/egresados/nuevo', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador', 'utsag')
def nuevo_egresado():
    """Registro administrativo directo de un egresado y su cuenta opcional."""
    rol_activo = current_user.rol_activo_nombre()
    alcance = _alcance_programas(rol_activo, current_user.id_personal)

    curriculas_q = Curriculas.query.join(ProgramasEstudio).filter(Curriculas.estado == 'activo')
    if alcance is not None:
        curriculas_q = curriculas_q.filter(ProgramasEstudio.id_programa.in_(alcance)) if alcance else curriculas_q.filter(db.literal(False))
    curriculas = curriculas_q.order_by(ProgramasEstudio.nombre, Curriculas.nombre).all()

    if request.method == 'POST':
        dni = limpiar_texto(request.form.get('dni'), 15)
        codigo_uni = limpiar_texto(request.form.get('codigo_universitario'), 10) or None
        apellido_paterno = limpiar_texto(request.form.get('apellido_paterno'), 80)
        apellido_materno = limpiar_texto(request.form.get('apellido_materno'), 80) or None
        nombres = limpiar_texto(request.form.get('nombres'), 100)
        genero = limpiar_texto(request.form.get('genero'), 1) or None
        id_curricula = request.form.get('id_curricula', type=int)
        correo_inst = limpiar_texto(request.form.get('correo_institucional'), 150).lower() or None
        telefono = limpiar_texto(request.form.get('telefono'), 20) or None
        periodo = limpiar_texto(request.form.get('periodo'), 20) or None
        crear_cuenta = bool(request.form.get('crear_cuenta'))
        contrasena = request.form.get('contrasena', '').strip()

        try:
            anio_ingreso = entero_en_rango(request.form.get('anio_ingreso'), 1950, 2100, obligatorio=False)
            anio_egreso = entero_en_rango(request.form.get('anio_egreso'), 1950, 2100, obligatorio=False)
        except ValueError as exc:
            flash(str(exc), 'warning')
            return render_template('admin/nuevo_egresado.html', curriculas=curriculas, form_data=request.form)

        if not dni or not apellido_paterno or not nombres or not id_curricula:
            flash('DNI, apellido paterno, nombres y plan curricular son obligatorios.', 'warning')
            return render_template('admin/nuevo_egresado.html', curriculas=curriculas, form_data=request.form)

        curricula_obj = db.session.get(Curriculas, id_curricula)
        if not curricula_obj or (alcance is not None and curricula_obj.id_programa not in alcance):
            flash('El plan curricular seleccionado no es válido o está fuera de tu ámbito.', 'danger')
            return render_template('admin/nuevo_egresado.html', curriculas=curriculas, form_data=request.form)

        if Egresados.query.filter_by(dni=dni).first():
            flash('Ya existe un egresado registrado con ese DNI.', 'warning')
            return render_template('admin/nuevo_egresado.html', curriculas=curriculas, form_data=request.form)

        if codigo_uni and Egresados.query.filter_by(codigo_universitario=codigo_uni).first():
            flash('Ya existe un egresado con ese código universitario.', 'warning')
            return render_template('admin/nuevo_egresado.html', curriculas=curriculas, form_data=request.form)

        if crear_cuenta:
            if not correo_inst or len(contrasena) < 8:
                flash('Para crear cuenta debes indicar un correo y una contraseña de al menos 8 caracteres.', 'warning')
                return render_template('admin/nuevo_egresado.html', curriculas=curriculas, form_data=request.form)
            if Usuarios.query.filter_by(correo=correo_inst).first():
                flash('Ese correo ya tiene una cuenta registrada.', 'warning')
                return render_template('admin/nuevo_egresado.html', curriculas=curriculas, form_data=request.form)

        egresado = Egresados(
            dni=dni,
            codigo_universitario=codigo_uni,
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            nombres=nombres,
            genero=genero if genero in ('M', 'F') else None,
            correo_institucional=correo_inst,
            telefono=telefono,
            id_curricula=curricula_obj.id_curricula,
            anio_ingreso=anio_ingreso,
            anio_egreso=anio_egreso,
            periodo=periodo,
        )
        db.session.add(egresado)
        db.session.flush()

        if crear_cuenta:
            usuario = Usuarios(
                correo=correo_inst,
                contrasena_hash=bcrypt.generate_password_hash(contrasena).decode('utf-8'),
                id_egresado=egresado.id_egresado,
                estado='activo',
            )
            db.session.add(usuario)
            db.session.flush()
            rol_egr = Roles.query.filter_by(nombre='egresado').first()
            if rol_egr:
                db.session.add(UsuarioRoles(id_usuario=usuario.id_usuario, id_rol=rol_egr.id_rol))

        db.session.commit()
        registrar_auditoria(
            'crear_egresado_admin', 'academico', 'egresados', egresado.id_egresado,
            resultado='exito', detalle=f'Cuenta creada: {crear_cuenta}'
        )
        flash(f'Egresado {egresado.nombre_completo()} registrado correctamente.', 'success')
        return redirect(url_for('admin.ver_egresado', id=egresado.id_egresado))

    return render_template('admin/nuevo_egresado.html', curriculas=curriculas, form_data=None)


@admin.route('/admin/egresados/<int:id>')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def ver_egresado(id):
    e = Egresados.query.get_or_404(id)
    rol_activo = current_user.rol_activo_nombre()
    alcance = _alcance_programas(rol_activo, current_user.id_personal)

    if alcance is not None:
        id_programa = e.curricula.id_programa if e.curricula else None
        if id_programa not in alcance:
            flash('No tienes permiso para ver este egresado.', 'danger')
            return redirect(url_for('admin.egresados'))

    return render_template('admin/ver_egresado.html', e=e)


@admin.route('/admin/egresados/exportar')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def exportar_egresados():
    rol_activo = current_user.rol_activo_nombre()
    alcance    = _alcance_programas(rol_activo, current_user.id_personal)

    q = Egresados.query.join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)

    if alcance is not None:
        q = q.filter(Curriculas.id_programa.in_(alcance)) if alcance else q.filter(db.literal(False))

    id_facultad = request.args.get('id_facultad', type=int)
    id_programa = request.args.get('id_programa', type=int)
    if id_programa:
        q = q.filter(Curriculas.id_programa == id_programa)
    elif id_facultad:
        q = q.join(ProgramasEstudio, Curriculas.id_programa == ProgramasEstudio.id_programa)\
             .filter(ProgramasEstudio.id_facultad == id_facultad)

    buscar        = request.args.get('buscar', '').strip()
    genero        = request.args.get('genero', '')
    curricula     = request.args.get('curricula', '')
    anio_ingreso  = request.args.get('anio_ingreso', '')
    anio_egreso   = request.args.get('anio_egreso', '')
    letra_periodo = request.args.get('letra_periodo', '')
    nivel         = request.args.get('nivel', '')

    if buscar:
        like = f'%{buscar}%'
        q = q.filter(db.or_(
            Egresados.nombres.ilike(like), Egresados.apellido_paterno.ilike(like),
            Egresados.apellido_materno.ilike(like), Egresados.codigo_universitario.ilike(like),
            Egresados.dni.ilike(like),
        ))
    if genero:        q = q.filter(Egresados.genero == genero)
    if curricula:      q = q.filter(Curriculas.nombre.ilike(f'%{curricula}%'))
    if anio_ingreso and anio_ingreso.isdigit():
        q = q.filter(Egresados.anio_ingreso == int(anio_ingreso))
    if anio_egreso and anio_egreso.isdigit():
        q = q.filter(Egresados.anio_egreso == int(anio_egreso))
    if letra_periodo:  q = q.filter(Egresados.periodo.ilike(f'%{letra_periodo}'))
    if nivel:
        jerarquia = ['egresado', 'bachiller', 'titulado', 'maestria', 'doctorado', 'phd']
        if nivel.startswith('solo_'):
            q = q.filter(Egresados.nivel_maximo == nivel.replace('solo_', ''))
        elif nivel in jerarquia:
            q = q.filter(Egresados.nivel_maximo.in_(jerarquia[jerarquia.index(nivel):]))

    egresados = q.order_by(Egresados.apellido_paterno).all()

    columnas = [
        ('Código universitario', lambda e: e.codigo_universitario or ''),
        ('DNI',                  lambda e: e.dni),
        ('Apellido paterno',     lambda e: e.apellido_paterno),
        ('Apellido materno',     lambda e: e.apellido_materno or ''),
        ('Nombres',              lambda e: e.nombres),
        ('Correo institucional', lambda e: e.correo_institucional or ''),
        ('Teléfono',             lambda e: e.telefono or ''),
        ('Género',               lambda e: 'Masculino' if e.genero=='M' else 'Femenino' if e.genero=='F' else (e.genero or '')),
        ('Currícula',            lambda e: e.curricula.nombre if e.curricula else ''),
        ('Programa',             lambda e: e.curricula.programa.nombre if e.curricula else ''),
        ('Facultad',             lambda e: e.curricula.programa.facultad.nombre if e.curricula else ''),
        ('Año de ingreso',       lambda e: e.anio_ingreso or ''),
        ('Año de egreso',        lambda e: e.anio_egreso or ''),
        ('Período',              lambda e: e.periodo or ''),
        ('Provincia',            lambda e: e.provincia or ''),
        ('Región',               lambda e: e.region or ''),
        ('País',                 lambda e: e.pais),
        ('Nivel académico máximo', lambda e: e.nivel_maximo.capitalize()),
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = 'Egresados'
    ws.append([c[0] for c in columnas])
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='003876', end_color='003876', fill_type='solid')
        cell.alignment = Alignment(horizontal='center')
    for e in egresados:
        ws.append([_celda_excel_segura(c[1](e)) for c in columnas])
    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 35)

    mem = io.BytesIO()
    wb.save(mem)
    mem.seek(0)
    return send_file(mem, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='egresados.xlsx')


@admin.route('/admin/programas-por-facultad')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def programas_por_facultad():
    id_facultad = request.args.get('id_facultad', type=int)
    if not id_facultad:
        return jsonify([])
    rol = current_user.rol_activo_nombre()
    alcance = _alcance_programas(rol, current_user.id_personal)
    q = ProgramasEstudio.query.filter_by(id_facultad=id_facultad)
    if alcance is not None:
        q = q.filter(ProgramasEstudio.id_programa.in_(alcance)) if alcance else q.filter(db.literal(False))
    programas = q.order_by(ProgramasEstudio.nombre).all()
    return jsonify([{'id': p.id_programa, 'nombre': p.nombre} for p in programas])


@admin.route('/admin/egresados/<int:id>/pdf')
@login_required
@requiere_rol('administrador', 'coordinador', 'utsag')
def exportar_egresado_pdf(id):
    from app.utils.cv_pdf import generar_cv
    from app.models import Habilidades
    e            = Egresados.query.get_or_404(id)
    rol = current_user.rol_activo_nombre()
    alcance = _alcance_programas(rol, current_user.id_personal)
    # Exportar un CV contiene datos personales: comprobar el mismo ámbito que la ficha.
    id_programa_egresado = e.curricula.id_programa if e.curricula else None
    if alcance is not None and id_programa_egresado not in alcance:
        from flask import abort
        abort(403)
    empleos      = Empleos.query.filter_by(id_egresado=id)\
                                .order_by(Empleos.fecha_inicio.desc()).all()
    logros       = TrayectoriaAcademica.query.filter_by(id_egresado=id)\
                                .order_by(TrayectoriaAcademica.fecha_obtencion).all()
    todos_certificados = Certificados.query.filter_by(id_egresado=id).all()
    certificados = [c for c in todos_certificados if c.categoria != 'idioma']
    idiomas      = [c for c in todos_certificados if c.categoria == 'idioma']
    habilidades  = Habilidades.query.filter_by(id_egresado=id, tipo='habilidad').all()
    intereses    = Habilidades.query.filter_by(id_egresado=id, tipo='interes').all()

    pdf = generar_cv(e, empleos, logros, certificados, habilidades, intereses, idiomas)
    nombre = f"Perfil_{e.apellido_paterno}_{e.nombres.split()[0]}.pdf"
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=nombre)