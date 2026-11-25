"""V10.6: registra el código curricular confirmado, con fecha de inicio pendiente.

No cambia usuarios, egresados, roles ni datos de otros programas.
Modo lectura por defecto; --aplicar requiere tabla con anio_inicio nullable.
Cuando conozcas el año oficial: --anio-inicio AAAA --aplicar.
"""
import argparse
from sqlalchemy import text
from app import create_app
from app.extensions import db
from app.models import Facultades, ProgramasEstudio, Curriculas
from app.ambito import FACULTAD, PROGRAMA, CURRICULA_CONFIRMADA_API, normalizar


def ejecutar(aplicar, anio):
    facultades = [x for x in Facultades.query.all() if normalizar(x.nombre) == normalizar(FACULTAD)]
    if len(facultades) != 1:
        raise RuntimeError('Debe existir exactamente una Facultad de Ingeniería. No se creó ni modificó nada.')
    facultad = facultades[0]
    programas = [x for x in ProgramasEstudio.query.all() if normalizar(x.nombre) == normalizar(PROGRAMA) and x.id_facultad == facultad.id_facultad]
    if len(programas) != 1:
        raise RuntimeError('Debe existir exactamente un programa Sistemas asociado a Ingeniería. No se modificó nada.')
    p = programas[0]
    if p.estado != 'activo':
        raise RuntimeError('El programa figura inactivo. Revisa el catálogo con el administrador.')

    columna = db.session.execute(text("""SELECT IS_NULLABLE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='curriculas' AND COLUMN_NAME='anio_inicio' """ )).scalar()
    if columna is None:
        raise RuntimeError('No existe la columna anio_inicio. Revisa el esquema de MySQL.')
    print('Tabla curriculas: anio_inicio permite NULL:', 'SÍ' if columna == 'YES' else 'NO')

    planes = Curriculas.query.filter_by(id_programa=p.id_programa, nombre=CURRICULA_CONFIRMADA_API).all()
    if len(planes) > 1:
        raise RuntimeError('Hay currículas 17A4SI duplicadas; revisa antes de continuar.')
    curr = planes[0] if planes else None
    if curr and curr.estado != 'activo':
        raise RuntimeError('El plan existe pero está inactivo. Revisa el estado antes de continuar.')
    if curr and anio is not None and curr.anio_inicio is not None and int(curr.anio_inicio) != anio:
        raise RuntimeError('Año existente diferente: no se modificará automáticamente.')

    print(f'Facultad: {facultad.nombre} (ID {facultad.id_facultad})')
    print(f'Programa: {p.nombre} (ID {p.id_programa})')
    if curr:
        print('Currícula 17A4SI: ya registrada', f'(anio inicio: {curr.anio_inicio if curr.anio_inicio is not None else "PENDIENTE"})')
    else:
        print('Currícula 17A4SI: aún no registrada')
    if not aplicar:
        print('MODO LECTURA. Para crear o completar el registro: --aplicar')
        return
    if not curr and anio is None and columna != 'YES':
        raise RuntimeError('Primero ejecuta 01_PERMITIR_ANIO_PENDIENTE_MYSQL.sql en Workbench con root.')
    if not curr:
        curr = Curriculas(id_programa=p.id_programa, nombre=CURRICULA_CONFIRMADA_API, anio_inicio=anio, estado='activo')
        db.session.add(curr)
    elif curr.anio_inicio is None and anio is not None:
        curr.anio_inicio = anio
    db.session.commit()
    print('[OK] Currícula 17A4SI lista para su relación con egresados verificados.')
    if curr.anio_inicio is None:
        print('[PENDIENTE] Año oficial de inicio: aún no confirmado. NO se inventó.')
    print('No se alteraron usuarios, egresados ni facultades históricas.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--aplicar', action='store_true', help='Autoriza crear el plan sin año o completar el año validado')
    parser.add_argument('--anio-inicio', type=int, help='Solo cuando esté confirmado oficialmente')
    args=parser.parse_args()
    if args.anio_inicio is not None and not 1950 <= args.anio_inicio <= 2100:
        parser.error('Año fuera del rango admitido')
    app=create_app()
    with app.app_context():
        try:
            ejecutar(args.aplicar, args.anio_inicio)
        except Exception:
            db.session.rollback()
            raise

if __name__=='__main__':
    main()
