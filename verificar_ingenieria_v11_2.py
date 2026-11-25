"""Diagnostico no destructivo, sin mostrar passwords, DNIs ni direcciones."""
import os
import sys
from pathlib import Path
from sqlalchemy import text
from app import create_app
from app.extensions import db


def marcar(clave, correcto, detalle=''):
    print(f"[{'OK' if correcto else 'AVISO'}] {clave}" + (f': {detalle}' if detalle else ''))
    return bool(correcto)


def main():
    raiz=Path(__file__).resolve().parent
    print('NEXO UNDAC V11.2 | DIAGNOSTICO DE INGENIERIA (SOLO LECTURA)')
    correcto=True
    for archivo in ('wsgi.py','app/ops_v11_2.py','app/observabilidad_v11_2.py',
                    'app/static/js/v11_indicadores.js','tests/test_v11_2_ingenieria.py'):
        estado=(raiz/archivo).is_file()
        correcto &= marcar('Archivo', estado, archivo)
    app=create_app()
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1')).scalar()
            correcto &= marcar('MySQL',True,'conexion confirmada')
        except Exception:
            marcar('MySQL',False,'no conectado; revisa .env y servicio MySQL84')
            correcto=False
        for tabla in ('egresados','usuarios','curriculas','programas_estudio'):
            try:
                db.session.execute(text(f'SELECT 1 FROM `{tabla}` LIMIT 1')).all()
                correcto &= marcar('Tabla',True,tabla)
            except Exception:
                marcar('Tabla',False,tabla);correcto=False
        db.session.remove()
    # Verifica cabeceras y las dos rutas de salud sin imprimir configuracion sensible.
    with app.test_client() as cliente:
        viva=cliente.get('/health/live')
        marcar('Liveness',viva.status_code==200,str(viva.status_code))
        correcta=(viva.headers.get('X-Request-ID') is not None)
        correcto &= marcar('Identificador de solicitud',correcta)
        lista=cliente.get('/health/ready')
        correcto &= marcar('Readiness',lista.status_code==200,str(lista.status_code))
        protegida=cliente.get('/admin/api/v11/indicadores',follow_redirects=False)
        correcto &= marcar('API sin sesion protegida',protegida.status_code in (302,401,403),str(protegida.status_code))
    marcar('Alcance Sistemas',app.config.get('SOLO_SISTEMAS',False))
    clave=app.config.get('SECRET_KEY')
    marcar('SECRET_KEY configurada',bool(clave) and len(str(clave))>=32)
    if not app.config.get('SESSION_COOKIE_SECURE'):
        print('[INFO] Cookie Secure desactivada: aceptable SOLO para pruebas HTTP locales; HTTPS imprescindible en internet.')
    print('[INFO] No se han modificado registros ni tablas.')
    print('[RESULTADO] '+'CHECKS OPERATIVOS CORRECTOS' if correcto else '[RESULTADO] VERIFICA LOS AVISOS')
    return 0 if correcto else 1

if __name__=='__main__': sys.exit(main())
