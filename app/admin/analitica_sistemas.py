"""Gráficos basados exclusivamente en registros del ámbito autorizado.

Distinguen: cuenta activa, empleo reportado y ausencia de declaración laboral.
Un enlace abierto no se interpreta como empleo obtenido.
"""
from sqlalchemy import func
from app.extensions import db
from app.models import (Egresados, Curriculas, Empleos, Usuarios, Habilidades,
                        Respuestas)
from app.admin.helpers import _alcance_programas


def construir_analitica(rol, id_personal):
    ids = _alcance_programas(rol, id_personal)
    q = db.session.query(Egresados.id_egresado).join(
        Curriculas, Egresados.id_curricula == Curriculas.id_curricula)
    if ids is not None:
        q = q.filter(Curriculas.id_programa.in_(ids))
    ids_eg = q.subquery()
    filtro = Egresados.id_egresado.in_(ids_eg)

    registrados = db.session.query(func.count(Egresados.id_egresado)).filter(filtro).scalar() or 0
    con_cuenta = db.session.query(func.count(func.distinct(Usuarios.id_egresado))).filter(
        Usuarios.id_egresado.in_(ids_eg), Usuarios.estado == 'activo').scalar() or 0
    con_empleo = db.session.query(func.count(func.distinct(Empleos.id_egresado))).filter(
        Empleos.id_egresado.in_(ids_eg), Empleos.es_actual == 1).scalar() or 0

    raw_promos = db.session.query(Egresados.anio_egreso, func.count(Egresados.id_egresado))\
        .filter(filtro, Egresados.anio_egreso.isnot(None))\
        .group_by(Egresados.anio_egreso).order_by(Egresados.anio_egreso.desc()).limit(10).all()
    raw_promos = sorted(raw_promos, key=lambda x: x[0])
    maximo = max((n for _, n in raw_promos), default=0)
    promociones = [{'anio': str(y), 'total': int(n),
                    'pct': round(n / maximo * 100, 1) if maximo else 0} for y, n in raw_promos]

    raw_curriculas = db.session.query(Curriculas.nombre, func.count(Egresados.id_egresado))\
        .select_from(Egresados).join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)\
        .filter(filtro).group_by(Curriculas.nombre).order_by(func.count(Egresados.id_egresado).desc()).all()
    maxcurr = max((n for _, n in raw_curriculas), default=0)
    curriculas = [{'nombre': nombre, 'total': int(n),
                  'pct': round(n / maxcurr * 100, 1) if maxcurr else 0}
                 for nombre, n in raw_curriculas]

    raw_hab = db.session.query(Habilidades.nombre, func.count(Habilidades.id_habilidad))\
        .filter(Habilidades.id_egresado.in_(ids_eg), Habilidades.tipo == 'habilidad')\
        .group_by(Habilidades.nombre).order_by(func.count(Habilidades.id_habilidad).desc()).limit(6).all()
    mh = max((n for _, n in raw_hab), default=0)
    habilidades = [{'nombre': nombre, 'total': int(n), 'pct': round(n/mh*100, 1) if mh else 0}
                   for nombre, n in raw_hab]
    respuestas = db.session.query(func.count(func.distinct(Respuestas.id_egresado)))\
        .filter(Respuestas.id_egresado.in_(ids_eg)).scalar() or 0
    return {'total': registrados, 'cuentas': con_cuenta,
            'porc_cuentas': round(100*con_cuenta/registrados, 1) if registrados else 0,
            'empleos': con_empleo,
            'porc_empleo_reportado': round(100*con_empleo/registrados, 1) if registrados else 0,
            'sin_empleo_informado': max(0, registrados-con_empleo),
            'participantes_encuestas': respuestas,
            'promociones': promociones, 'curriculas': curriculas, 'habilidades': habilidades}
