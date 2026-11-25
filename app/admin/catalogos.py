"""Catálogos oficiales gestionados desde el panel (no consulta automática a la API)."""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy.exc import IntegrityError
from app.admin import admin
from app.admin.helpers import requiere_rol
from app.extensions import db
from app.models import Facultades, ProgramasEstudio, Curriculas
from app.utils.v8_csrf import token_v8, validar_v8
from app.ambito import FACULTAD, PROGRAMA, es_programa_sistemas, normalizar, ids_programa_sistemas, solo_sistemas


@admin.route('/admin/catalogos', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador')
def catalogos():
    if request.method == 'POST':
        validar_v8()
        accion = request.form.get('accion')
        try:
            if accion == 'facultad':
                nombre = request.form.get('nombre', '').strip()
                codigo = request.form.get('codigo', '').strip() or None
                if not nombre:
                    raise ValueError('Indica el nombre oficial de la facultad.')
                if solo_sistemas() and normalizar(nombre) != normalizar(FACULTAD):
                    raise ValueError('El catálogo habilitado corresponde a la Facultad de Ingeniería.')
                db.session.add(Facultades(nombre=nombre, codigo=codigo, estado='activo'))
            elif accion == 'programa':
                facultad = Facultades.query.get(request.form.get('id_facultad', type=int))
                nombre = request.form.get('nombre', '').strip()
                codigo = request.form.get('codigo', '').strip() or None
                if not facultad or not nombre:
                    raise ValueError('Elige una facultad válida y el nombre académico.')
                if solo_sistemas() and (not es_programa_sistemas(nombre) or normalizar(facultad.nombre) != normalizar(FACULTAD)):
                    raise ValueError('Este sistema gestiona exclusivamente Ingeniería de Sistemas y Computación.')
                db.session.add(ProgramasEstudio(id_facultad=facultad.id_facultad, nombre=nombre,
                                                codigo=codigo, estado='activo'))
            elif accion == 'curricula':
                programa = ProgramasEstudio.query.get(request.form.get('id_programa', type=int))
                nombre = request.form.get('nombre', '').strip()
                anio_texto = (request.form.get('anio_inicio') or '').strip()
                if not programa or not nombre:
                    raise ValueError('Selecciona el programa e indica el código oficial de currícula.')
                if anio_texto:
                    if not anio_texto.isdigit() or not 1950 <= int(anio_texto) <= 2100:
                        raise ValueError('El año debe ser un año oficial entre 1950 y 2100.')
                    anio = int(anio_texto)
                else:
                    anio = None
                    # Solo se admite pendiente de año para el código confirmado por API.
                    if nombre.upper() != '17A4SI' or not es_programa_sistemas(programa.nombre):
                        raise ValueError('Confirma el año de inicio para este plan antes de registrarlo.')
                if solo_sistemas() and not es_programa_sistemas(programa.nombre):
                    raise ValueError('La currícula debe pertenecer a Ingeniería de Sistemas y Computación.')
                if Curriculas.query.filter_by(id_programa=programa.id_programa, nombre=nombre).first():
                    raise ValueError('Esa currícula ya existe para el programa.')
                db.session.add(Curriculas(id_programa=programa.id_programa, nombre=nombre,
                                          anio_inicio=anio, estado='activo'))
            else:
                raise ValueError('Operación desconocida.')
            db.session.commit()
            flash('Catálogo académico actualizado.', 'success')
        except (ValueError, IntegrityError) as e:
            db.session.rollback()
            flash(str(e) if isinstance(e, ValueError) else 'Ya existe un registro con ese nombre o código.', 'danger')
        return redirect(url_for('admin.catalogos'))
    if solo_sistemas():
        facultades = [f for f in Facultades.query.order_by(Facultades.nombre).all()
                     if normalizar(f.nombre) == normalizar(FACULTAD)]
        programas = [p for p in ProgramasEstudio.query.order_by(ProgramasEstudio.nombre).all()
                     if es_programa_sistemas(p.nombre)]
        curriculas = [c for c in Curriculas.query.all() if c.id_programa in {p.id_programa for p in programas}]
    else:
        facultades = Facultades.query.order_by(Facultades.nombre).all()
        programas = ProgramasEstudio.query.order_by(ProgramasEstudio.nombre).all()
        curriculas = Curriculas.query.order_by(Curriculas.id_curricula.desc()).limit(100).all()
    return render_template('admin/catalogos.html', csrf_admin=token_v8(),
                           facultades=facultades, programas=programas, curriculas=curriculas)
