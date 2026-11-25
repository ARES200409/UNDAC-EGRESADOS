"""Registra Facultad de Ingeniería, programa Sistemas y plan 17A4SI sin borrar registros.

El código 17A4SI se observó en la API; el año oficial del plan NO se deduce
ni se debe adivinar. Por ello --anio-inicio es obligatorio al crear el plan.
"""
import argparse
from app import create_app
from app.extensions import db
from app.models import Facultades, ProgramasEstudio, Curriculas
from app.ambito import FACULTAD, PROGRAMA, CURRICULA_CONFIRMADA_API, normalizar


def ejecutar(anio):
    facultades = [f for f in Facultades.query.all() if normalizar(f.nombre) == normalizar(FACULTAD)]
    if len(facultades) > 1:
        raise ValueError('Hay dos facultades equivalentes; revisar manualmente antes de continuar.')
    f = facultades[0] if facultades else None
    if not f and anio is None:
        print('Sin Facultad de Ingeniería. Se requiere --anio-inicio para crear el conjunto.')
        return
    if not f:
        f = Facultades(nombre=FACULTAD, estado='activo')
        db.session.add(f)
        db.session.flush()
    programas = [p for p in ProgramasEstudio.query.all() if normalizar(p.nombre) == normalizar(PROGRAMA)]
    if len(programas) > 1:
        raise ValueError('Hay programas Sistemas duplicados; resolver antes de continuar.')
    p = programas[0] if programas else None
    if p is not None and p.id_facultad != f.id_facultad:
        raise ValueError('El programa existe vinculado a otra facultad. Corregir de forma autorizada.')
    if not p and anio is None:
        print('El programa aún no existe. Confirma el año oficial y ejecuta con --anio-inicio.')
        return
    if not p:
        p = ProgramasEstudio(id_facultad=f.id_facultad, nombre=PROGRAMA, estado='activo')
        db.session.add(p)
        db.session.flush()
    curricula = Curriculas.query.filter_by(id_programa=p.id_programa,
                                            nombre=CURRICULA_CONFIRMADA_API).first()
    if not curricula and anio is None:
        print(f'Programa encontrado (ID {p.id_programa}), pero el plan {CURRICULA_CONFIRMADA_API} no existe.')
        print('No se modificó la BD. Confirma el año oficial y usa --anio-inicio AAAA.')
        db.session.rollback()
        return
    if not curricula:
        curricula = Curriculas(id_programa=p.id_programa, nombre=CURRICULA_CONFIRMADA_API,
                               anio_inicio=anio, estado='activo')
        db.session.add(curricula)
    elif anio is not None and int(curricula.anio_inicio) != anio:
        raise ValueError('El plan existente tiene otro año. No se sobrescribirá automáticamente.')
    db.session.commit()
    print('Catálogo de Sistemas verificado / preparado correctamente.')
    print(f'  Facultad: {f.nombre} (ID {f.id_facultad})')
    print(f'  Programa: {p.nombre} (ID {p.id_programa})')
    print(f'  Currícula: {curricula.nombre}; año inicio: {curricula.anio_inicio}')
    print('No se eliminaron egresados, roles, cuentas ni facultades anteriores.')


def main():
    parser=argparse.ArgumentParser(description='Configurar catálogo académico de Sistemas sin eliminar datos')
    parser.add_argument('--anio-inicio', type=int, help='Año oficial confirmado para el plan 17A4SI (obligatorio si aún no existe)')
    a=parser.parse_args()
    if a.anio_inicio is not None and not 1950<=a.anio_inicio<=2100:
        parser.error('El año debe estar entre 1950 y 2100')
    app=create_app()
    with app.app_context():
        try: ejecutar(a.anio_inicio)
        except Exception:
            db.session.rollback()
            raise
if __name__=='__main__': main()
