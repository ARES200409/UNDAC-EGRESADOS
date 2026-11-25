"""Ámbito de NEXO Sistemas. No borra ni migra registros históricos.

La comparación del programa es exacta tras normalizar tildes/espacios.
No se infiere el plan curricular a partir del año de ingreso ni del código documental.
"""
import unicodedata
from flask import current_app

PROGRAMA = 'Ingeniería de Sistemas y Computación'
FACULTAD = 'Facultad de Ingeniería'
CURRICULA_CONFIRMADA_API = '17A4SI'  # Observada en respuestas de la API; no demuestra su año de inicio.

def normalizar(valor):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(valor or ''))
                             if not unicodedata.combining(c)).casefold().split())

def solo_sistemas():
    return bool(current_app.config.get('SOLO_SISTEMAS', True))

def es_programa_sistemas(nombre):
    return normalizar(nombre) == normalizar(PROGRAMA)

def ids_programa_sistemas():
    from app.models import ProgramasEstudio
    if not solo_sistemas():
        return None
    return [p.id_programa for p in ProgramasEstudio.query.filter_by(estado='activo').all()
            if es_programa_sistemas(p.nombre)]

def validar_programa_api(datos):
    return isinstance(datos, dict) and (
        not solo_sistemas() or es_programa_sistemas(datos.get('Programa facultad'))
    )

def es_egresado_en_ambito(egresado):
    if not solo_sistemas():
        return True
    return bool(egresado and egresado.curricula and egresado.curricula.programa
                and es_programa_sistemas(egresado.curricula.programa.nombre))

def ids_facultad_sistemas():
    from app.models import ProgramasEstudio
    from app.extensions import db
    ids = ids_programa_sistemas()
    if ids is None:
        return None
    return [f[0] for f in db.session.query(
        ProgramasEstudio.id_facultad).filter(ProgramasEstudio.id_programa.in_(ids)).distinct().all()] if ids else []
