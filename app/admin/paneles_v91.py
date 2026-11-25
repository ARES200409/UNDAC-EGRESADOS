"""Paneles V9.1: información realmente distinta según responsabilidad.

Toda cifra se deriva de SQL; los alcances de coordinador/docente parten de
asignaciones_personal activas. No se consideran empleados a quienes no
reportan empleo; no se presupone situación de desempleo.
"""
from datetime import date
from sqlalchemy import func, and_
from app.extensions import db
from app.models import (
    AsignacionesPersonal, Curriculas, Egresados, Empleos, Encuesta,
    Empresas, Facultades, OfertasLaborales, Personal, Postulaciones,
    ProgramasEstudio, Respuestas, Roles, Usuarios,
)
from app.admin.helpers import _alcance_programas, _facultades_de_coordinador
from app.ambito import ids_programa_sistemas
from app.utils.v8_db import tablas_v8_disponibles


def _filas_programas(ids):
    if not ids:
        return []
    return db.session.query(
        ProgramasEstudio.id_programa.label('id'),
        ProgramasEstudio.nombre.label('nombre'),
        func.count(func.distinct(Egresados.id_egresado)).label('total'),
        func.count(func.distinct(Usuarios.id_usuario)).label('cuentas'),
    ).outerjoin(Curriculas, Curriculas.id_programa == ProgramasEstudio.id_programa)\
     .outerjoin(Egresados, Egresados.id_curricula == Curriculas.id_curricula)\
     .outerjoin(Usuarios, Usuarios.id_egresado == Egresados.id_egresado)\
     .filter(ProgramasEstudio.id_programa.in_(ids))\
     .group_by(ProgramasEstudio.id_programa, ProgramasEstudio.nombre)\
     .order_by(ProgramasEstudio.nombre).all()


def _filas_facultades():
    ids = ids_programa_sistemas()
    if ids is not None and not ids:
        return []
    q = db.session.query(
        Facultades.id_facultad.label('id'),
        Facultades.nombre.label('nombre'),
        func.count(func.distinct(Egresados.id_egresado)).label('total'),
        func.count(func.distinct(Usuarios.id_usuario)).label('cuentas'),
    ).outerjoin(ProgramasEstudio, ProgramasEstudio.id_facultad == Facultades.id_facultad)\
     .outerjoin(Curriculas, Curriculas.id_programa == ProgramasEstudio.id_programa)\
     .outerjoin(Egresados, Egresados.id_curricula == Curriculas.id_curricula)\
     .outerjoin(Usuarios, Usuarios.id_egresado == Egresados.id_egresado)\
     .group_by(Facultades.id_facultad, Facultades.nombre)\
     .order_by(Facultades.nombre)
    if ids is not None:
        q = q.filter(ProgramasEstudio.id_programa.in_(ids))
    return q.all()


def _participantes_en_ambito():
    ids = ids_programa_sistemas()
    q = db.session.query(func.count(func.distinct(Respuestas.id_egresado)))\
        .join(Egresados, Egresados.id_egresado == Respuestas.id_egresado)\
        .join(Curriculas, Curriculas.id_curricula == Egresados.id_curricula)
    if ids is not None:
        q = q.filter(Curriculas.id_programa.in_(ids))
    return q.scalar() or 0


def construir_contexto_panel(rol, id_personal, metricas):
    """No construye acceso privilegiado: requiere rol ya validado por la ruta."""
    m = metricas
    total = m['total']
    registrados = m['registrados']
    out = {
        'cobertura_pct': round(100 * registrados / total, 1) if total else None,
        'faltan_cuenta': max(0, total - registrados),
        'fecha_hoy': date.today(),
    }
    if rol == 'administrador':
        out.update(
            personal_total=Personal.query.count(),
            cuentas_personal=Usuarios.query.filter(Usuarios.id_personal.isnot(None)).count(),
            facultades_total=(Facultades.query.count() if ids_programa_sistemas() is None else
                db.session.query(func.count(func.distinct(ProgramasEstudio.id_facultad))).filter(
                    ProgramasEstudio.id_programa.in_(ids_programa_sistemas())).scalar() or 0),
            programas_total=(ProgramasEstudio.query.count() if ids_programa_sistemas() is None else len(ids_programa_sistemas())),
            encuestas_total=Encuesta.query.count(),
            empresas_total=Empresas.query.count(),
            ofertas_total=OfertasLaborales.query.count(),
            puestos_activos=OfertasLaborales.query.filter(
                OfertasLaborales.activa == 1,
                OfertasLaborales.fecha_vencimiento >= date.today()
            ).count(),
            postulaciones_total=(Postulaciones.query.count() if tablas_v8_disponibles() else None),
        )
    elif rol == 'utsag':
        out.update(
            facultades_resumen=_filas_facultades(),
            encuestas_publicadas=Encuesta.query.filter_by(estado='publicada').count(),
            encuestas_cerradas=Encuesta.query.filter_by(estado='cerrada').count(),
            participantes_encuestas=_participantes_en_ambito(),
        )
    elif rol == 'coordinador':
        fac_ids = _facultades_de_coordinador(id_personal)
        prog_ids = _alcance_programas(rol, id_personal) or []
        fac = Facultades.query.filter(Facultades.id_facultad.in_(fac_ids)).order_by(
            Facultades.nombre).all() if fac_ids else []
        rol_docente = Roles.query.filter_by(nombre='docente_responsable').first()
        docentes_total = 0
        if prog_ids and rol_docente:
            docentes_total = db.session.query(
                func.count(func.distinct(AsignacionesPersonal.id_personal))
            ).filter(
                AsignacionesPersonal.id_rol == rol_docente.id_rol,
                AsignacionesPersonal.estado == 'activo',
                AsignacionesPersonal.id_programa.in_(prog_ids),
            ).scalar() or 0
        out.update(
            facultades_asignadas=fac,
            programas_resumen=_filas_programas(prog_ids),
            docentes_total=docentes_total,
        )
    elif rol == 'docente_responsable':
        prog_ids = _alcance_programas(rol, id_personal) or []
        pendientes_anio = 0
        recientes = []
        if prog_ids:
            q = Egresados.query.join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)\
                .filter(Curriculas.id_programa.in_(prog_ids))
            pendientes_anio = q.filter(Egresados.anio_egreso.is_(None)).count()
            recientes = q.order_by(Egresados.creado_en.desc(), Egresados.id_egresado.desc())\
                .limit(6).all()
        out.update(
            programas_resumen=_filas_programas(prog_ids),
            pendientes_anio=pendientes_anio,
            egresados_recientes=recientes,
        )
    return out
