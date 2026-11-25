"""Prueba local de solo lectura. Ejecutar: python verificar_instalacion_v9.py"""
import sys
from pathlib import Path
from sqlalchemy import inspect, text
from app import create_app
from app.extensions import db

REQUIRED_TABLES = {
    'roles','usuarios','egresados','personal','asignaciones_personal','facultades',
    'programas_estudio','curriculas','empresas','ofertas_laborales','empleos',
    'encuestas','preguntas','opciones','respuestas','postulaciones',
    'ofertas_guardadas','seguimiento_externo'
}

def main():
    app = create_app()
    print('NEXO UNDAC V9 | Diagnóstico local (solo lectura)')
    print('Rutas Flask registradas:', len(list(app.url_map.iter_rules())))
    for nombre in app.jinja_env.list_templates():
        app.jinja_env.get_template(nombre)
    print('Plantillas Jinja verificadas:', len(app.jinja_env.list_templates()))
    with app.app_context():
        tablas=set(inspect(db.engine).get_table_names())
        faltantes=sorted(REQUIRED_TABLES-tablas)
        print('Tablas detectadas:', len(tablas))
        if faltantes:
            print('FALTANTES:',', '.join(faltantes))
            return 2
        print('Tablas V8 y V9: OK')
        roles=db.session.execute(text('SELECT nombre FROM roles ORDER BY nombre')).scalars().all()
        print('Roles registrados:', ', '.join(roles))
        triggers=db.session.execute(text('SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=:db'),{'db':db.engine.url.database}).scalars().all()
        print('Triggers encontrados:', ', '.join(triggers) if triggers else 'ninguno; revisar lógica académica')
    print('Verificaciones básicas completadas. Faltan pruebas manuales por rol y producción.')
    return 0
if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as ex:
        print('FALLO:',type(ex).__name__,str(ex)[:350])
        sys.exit(1)
