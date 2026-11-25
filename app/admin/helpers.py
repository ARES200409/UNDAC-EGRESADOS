# app/admin/helpers.py
from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user
from app.extensions import db
from app.models import Roles, AsignacionesPersonal, ProgramasEstudio, Respuestas, Egresados, Curriculas
from app.ambito import ids_programa_sistemas


def solo_admin(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if not current_user.is_authenticated or current_user.es_egresado():
            flash('No tienes permiso para acceder.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorado


def requiere_rol(*roles_permitidos):
    def decorador(f):
        @wraps(f)
        def decorado(*args, **kwargs):
            if not current_user.is_authenticated or current_user.es_egresado():
                flash('No tienes permiso para acceder.', 'danger')
                return redirect(url_for('auth.login'))
            if current_user.rol_activo_nombre() not in roles_permitidos:
                flash('No tienes permiso para acceder a esta sección.', 'danger')
                return redirect(url_for('admin.dashboard'))
            return f(*args, **kwargs)
        return decorado
    return decorador


def _facultades_de_coordinador(id_personal):
    rol_coord = Roles.query.filter_by(nombre='coordinador').first()
    if not rol_coord:
        return []
    asigs = AsignacionesPersonal.query.filter_by(
        id_personal=id_personal, id_rol=rol_coord.id_rol, estado='activo').all()
    ids_sistemas = ids_programa_sistemas()
    if ids_sistemas is None:
        return [a.id_facultad for a in asigs if a.id_facultad]
    facultades_sistemas = {p.id_facultad for p in ProgramasEstudio.query.filter(
        ProgramasEstudio.id_programa.in_(ids_sistemas)).all()}
    return [a.id_facultad for a in asigs if a.id_facultad in facultades_sistemas]


def _ids_personal_gestionado_por_coordinador(id_personal_coordinador):
    ids_facultades = _facultades_de_coordinador(id_personal_coordinador)
    rol_docente = Roles.query.filter_by(nombre='docente_responsable').first()
    if not ids_facultades or not rol_docente:
        return []
    filas = db.session.query(AsignacionesPersonal.id_personal)\
        .join(ProgramasEstudio, AsignacionesPersonal.id_programa == ProgramasEstudio.id_programa)\
        .filter(AsignacionesPersonal.id_rol == rol_docente.id_rol,
                AsignacionesPersonal.estado == 'activo',
                ProgramasEstudio.id_facultad.in_(ids_facultades))\
        .distinct().all()
    return [f[0] for f in filas]


def _coordinador_gestiona_a(id_personal_coordinador, id_personal_objetivo):
    return id_personal_objetivo in _ids_personal_gestionado_por_coordinador(id_personal_coordinador)


def _alcance_programas(rol_activo, id_personal):
    """None=global (solo si se desactiva el alcance); []=ningún programa autorizado.

    Nunca concede automáticamente el programa de Sistemas a un coordinador
    o docente previamente asignado a otra facultad.
    """
    ids_sistemas = ids_programa_sistemas()
    if rol_activo in ('administrador', 'utsag'):
        return ids_sistemas
    if rol_activo == 'coordinador':
        ids_fac = _facultades_de_coordinador(id_personal)
        permitidos = [p.id_programa for p in ProgramasEstudio.query.filter(
            ProgramasEstudio.id_facultad.in_(ids_fac)).all()] if ids_fac else []
    elif rol_activo == 'docente_responsable':
        rol_doc = Roles.query.filter_by(nombre='docente_responsable').first()
        if not rol_doc:
            return []
        asigs = AsignacionesPersonal.query.filter_by(
            id_personal=id_personal, id_rol=rol_doc.id_rol, estado='activo').all()
        permitidos = [a.id_programa for a in asigs if a.id_programa]
    else:
        return []
    if ids_sistemas is not None:
        permitidos = [p for p in permitidos if p in ids_sistemas]
    return list(dict.fromkeys(permitidos))


def _query_respuestas_filtradas(id_encuesta, id_facultad=None, id_programa=None, ids_programas_forzado=None):
    q = Respuestas.query.filter_by(id_encuesta=id_encuesta)
    necesita_join = id_facultad or id_programa or ids_programas_forzado is not None
    if necesita_join:
        q = q.join(Egresados, Respuestas.id_egresado == Egresados.id_egresado)\
             .join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)\
             .join(ProgramasEstudio, Curriculas.id_programa == ProgramasEstudio.id_programa)
        if ids_programas_forzado is not None:
            q = q.filter(ProgramasEstudio.id_programa.in_(ids_programas_forzado)) if ids_programas_forzado else q.filter(db.literal(False))
        if id_programa:
            q = q.filter(ProgramasEstudio.id_programa == id_programa)
        elif id_facultad:
            q = q.filter(ProgramasEstudio.id_facultad == id_facultad)
    return q