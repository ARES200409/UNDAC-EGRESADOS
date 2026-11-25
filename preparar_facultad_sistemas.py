#!/usr/bin/env python3
"""Prepara Facultad de Ingeniería y el Programa de Sistemas, sin crear currículas.

Por seguridad funciona inicialmente en modo lectura: --aplicar confirma dos
inserciones posibles y no modifica otras facultades ni reasigna usuarios.
"""
import argparse
from app import create_app
from app.extensions import db
from app.models import Facultades, ProgramasEstudio
from app.ambito import FACULTAD, PROGRAMA, normalizar

def ejecutar(aplicar=False):
    coincidencias_fac = [f for f in Facultades.query.all() if normalizar(f.nombre) == normalizar(FACULTAD)]
    coincidencias_prog = [p for p in ProgramasEstudio.query.all() if normalizar(p.nombre) == normalizar(PROGRAMA)]
    if len(coincidencias_fac) > 1 or len(coincidencias_prog) > 1:
        raise RuntimeError('Coincidencias académicas duplicadas: se necesita revisión manual. No se realizaron cambios.')
    fac = coincidencias_fac[0] if coincidencias_fac else None
    prog = coincidencias_prog[0] if coincidencias_prog else None
    if fac and fac.estado != 'activo':
        raise RuntimeError('La Facultad de Ingeniería está inactiva: revisar antes de utilizarla.')
    if prog and prog.estado != 'activo':
        raise RuntimeError('El programa de Sistemas está inactivo: revisar antes de utilizarlo.')
    if prog and (fac is None or prog.id_facultad != fac.id_facultad):
        raise RuntimeError('El programa Sistemas aparece vinculado a otra facultad; no se modificará automáticamente.')
    print('Catálogo académico para la administración de usuarios:')
    print(' Facultad:', FACULTAD, '(existente)' if fac else '(por crear)')
    print(' Programa:', PROGRAMA, '(existente)' if prog else '(por crear)')
    print(' Currícula 17A4SI: NO se crea; requiere su año oficial de inicio.')
    print(' Cuentas, asignaciones anteriores, registros de otras facultades: NO se alteran.')
    if not aplicar:
        print('Modo lectura. Para aplicar, ejecuta nuevamente con --aplicar.')
        return
    if not fac:
        fac=Facultades(nombre=FACULTAD, estado='activo')
        db.session.add(fac)
        db.session.flush()
    if not prog:
        prog=ProgramasEstudio(id_facultad=fac.id_facultad, nombre=PROGRAMA, estado='activo')
        db.session.add(prog)
        db.session.flush()
    db.session.commit()
    print('[OK] Facultad ID',fac.id_facultad,'· Programa ID',prog.id_programa)
    print('Ahora puedes entrar al administrador > Cuentas y roles > Editar')
    print('y asignar explícitamente los usuarios autorizados a Sistemas.')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Crear solo Facultad de Ingeniería y Sistemas sin inventar currícula')
    parser.add_argument('--aplicar', action='store_true', help='Confirma los cambios mínimos al catálogo')
    args=parser.parse_args()
    app=create_app()
    with app.app_context():
        try: ejecutar(args.aplicar)
        except Exception:
            db.session.rollback()
            raise
