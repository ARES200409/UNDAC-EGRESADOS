"""Diagnóstico V11 de solo lectura; no altera MySQL ni archivos del sistema."""
from pathlib import Path
from sqlalchemy import inspect, text
from app import create_app
from app.extensions import db
from app.ambito import ids_programa_sistemas


def main():
    raiz = Path(__file__).resolve().parent
    for path in ['app/static/js/v11_indicadores.js',
                 'app/static/css/v11_institucional.css',
                 'app/templates/admin/_v11_graficos_interactivos.html',
                 'app/templates/admin/_v11_resultados_egresados.html']:
        print('[OK]' if (raiz / path).is_file() else '[FALTA]', path)
    app = create_app()
    routes = {rule.rule for rule in app.url_map.iter_rules()}
    for item in ['/admin/api/v11/indicadores', '/admin/egresados', '/admin']:
        print('[OK]' if item in routes else '[FALTA]', 'Ruta', item)
    try:
        with app.app_context():
            db.session.execute(text('SELECT 1'))
            print('[OK] MySQL conectado')
            tablas = set(inspect(db.engine).get_table_names())
            for nombre in ['egresados', 'curriculas', 'programas_estudio', 'usuarios']:
                print('[OK]' if nombre in tablas else '[PENDIENTE]', 'Tabla', nombre)
            print('[DATO] Programas autorizados de Sistemas:', len(ids_programa_sistemas() or []))
    except Exception as exc:
        print('[AVISO] No se pudo verificar la conexión o esquema local:', type(exc).__name__)
    print('Diagnóstico terminado; no se ha modificado MySQL.')


if __name__ == '__main__':
    main()
