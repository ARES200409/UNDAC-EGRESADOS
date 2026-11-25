"""Verificación local de solo lectura. No modifica datos ni contraseñas."""
from sqlalchemy import text
from app import create_app
from app.extensions import db
from app.models import Roles, ProgramasEstudio, Curriculas, Egresados
from app.ambito import ids_programa_sistemas, es_programa_sistemas

app = create_app()
with app.app_context():
    try:
        db.session.execute(text('SELECT 1'))
        print('[OK] Conexión MySQL')
        print('[OK] Alcance Sistemas:', 'activado' if app.config.get('SOLO_SISTEMAS') else 'desactivado')
        ids = ids_programa_sistemas()
        programas = ProgramasEstudio.query.all()
        for p in programas:
            if es_programa_sistemas(p.nombre):
                print('[OK] Programa:', p.nombre, 'ID:', p.id_programa)
                planes = Curriculas.query.filter_by(id_programa=p.id_programa).all()
                print('     Planes:', ', '.join(c.nombre for c in planes) or '(sin registrar)')
        if ids == []:
            print('[PENDIENTE] No hay programa Sistemas en MySQL.')
            print('     Ejecuta preparar_facultad_sistemas.py para revisar el catálogo.')
        for r in ('administrador','utsag','coordinador','docente_responsable','egresado'):
            print(('[OK]' if Roles.query.filter_by(nombre=r).first() else '[PENDIENTE]'), 'Rol:', r)
        q = Egresados.query.join(Curriculas)
        if ids is not None:
            q = q.filter(Curriculas.id_programa.in_(ids))
        print('[DATO] Egresados Sistemas registrados:', q.count())
        for tabla in ('ofertas_guardadas','postulaciones','seguimiento_externo'):
            result=db.session.execute(text('SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:t'),{'t':tabla}).scalar()
            print(('[OK]' if result else '[PENDIENTE]'), 'Tabla:', tabla)
        print('Verificación de lectura terminada. No se modificó información.')
    except Exception as e:
        print('[ERROR] Comprueba conexión MySQL y tablas instaladas. Tipo:',type(e).__name__)
        raise SystemExit(1)
