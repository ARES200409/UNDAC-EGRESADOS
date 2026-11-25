# app/services/sunedu_service.py
"""Adaptador SUNEDU para NEXO UNDAC.

SUNEDU publica el Registro Nacional de Grados y Títulos en:
  https://enlinea.sunedu.gob.pe/verificacion-titulo/
  https://datos.gob.pe/dataset/sunedu-titulo-profesional-y-grado

Situación actual de APIs:
  - API REST con clave: NO existe API pública oficial documentada
    para consulta por DNI en tiempo real.
  - Dataset CSV público: sí disponible en datos.gob.pe (consulta
    offline sobre archivo descargado).
  - Scraping del portal: NO autorizado; viola términos de uso.

Estrategia implementada:
  1. Si SUNEDU_API_URL + SUNEDU_API_KEY están configurados
     (eventual API institucional futura): consultar API.
  2. Si SUNEDU_DATASET_CSV apunta a un archivo CSV descargado
     de datos.gob.pe: buscar localmente.
  3. Si ninguno: retornar disponible=False con motivo.

Para usar el dataset CSV:
  1. Descargar desde https://datos.gob.pe/dataset/sunedu-titulo-profesional-y-grado
  2. Guardarlo en data/sunedu_grados_titulos.csv (dentro del proyecto)
  3. Configurar en .env: SUNEDU_DATASET_CSV=data/sunedu_grados_titulos.csv
"""

import csv
import os
import unicodedata
from pathlib import Path

import requests
from flask import current_app


# ----------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------
def _config():
    return {
        "api_url": os.getenv("SUNEDU_API_URL", "").strip(),
        "api_key": os.getenv("SUNEDU_API_KEY", "").strip(),
        "csv_path": os.getenv("SUNEDU_DATASET_CSV", "").strip(),
    }


# ----------------------------------------------------------------
# Función principal: consulta por DNI
# ----------------------------------------------------------------
def consultar_sunedu(dni: str) -> dict:
    """Consulta grados y títulos en SUNEDU por DNI.

    Retorna:
    {
        "fuente": "sunedu",
        "disponible": True | False,
        "grados": [ { ... } ],   # lista (puede ser vacía)
        "motivo": str | None
    }
    """
    dni = str(dni or "").strip()
    if not dni.isdigit() or len(dni) != 8:
        return _respuesta_error("dni_invalido")

    cfg = _config()

    # Prioridad 1: API institucional configurada
    if cfg["api_url"] and cfg["api_key"]:
        return _consultar_via_api(dni, cfg)

    # Prioridad 2: Dataset CSV local
    if cfg["csv_path"]:
        return _consultar_via_csv(dni, cfg["csv_path"])

    # Sin fuente disponible
    return _respuesta_error("sin_credenciales")


# ----------------------------------------------------------------
# Consulta vía API (eventual)
# ----------------------------------------------------------------
def _consultar_via_api(dni: str, cfg: dict) -> dict:
    try:
        respuesta = requests.get(
            f"{cfg['api_url']}/dni/{dni}",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Accept": "application/json",
            },
            timeout=(5, 15),
        )
        if respuesta.status_code == 200:
            datos = respuesta.json()
            grados = _normalizar_grados_api(datos)
            return {
                "fuente": "sunedu",
                "disponible": True,
                "grados": grados,
                "motivo": None,
            }
        if respuesta.status_code == 404:
            return {
                "fuente": "sunedu",
                "disponible": True,
                "grados": [],
                "motivo": None,
            }
        return _respuesta_error(f"http_{respuesta.status_code}")
    except requests.exceptions.Timeout:
        return _respuesta_error("timeout")
    except requests.exceptions.ConnectionError:
        return _respuesta_error("conexion_fallida")
    except (requests.exceptions.RequestException, ValueError) as exc:
        current_app.logger.warning("SUNEDU API error: %s", exc)
        return _respuesta_error("error_inesperado")


# ----------------------------------------------------------------
# Consulta vía CSV local (dataset datos.gob.pe)
# ----------------------------------------------------------------
def _consultar_via_csv(dni: str, csv_path: str) -> dict:
    """Busca registros de grados/títulos en el CSV de SUNEDU.

    Se espera que el CSV tenga columnas como:
      DNI_GRADUADO, APELLIDO_PATERNO, APELLIDO_MATERNO, NOMBRES,
      GRADO_ACADEMICO, DESCRIPCION_GRADO, UNIVERSIDAD, FECHA_REGISTRO
    (El esquema exacto depende de la versión descargada.)
    """
    # Resolver ruta relativa al directorio del proyecto
    path = Path(csv_path)
    if not path.is_absolute():
        project_root = Path(current_app.root_path).parent
        path = project_root / csv_path

    if not path.exists():
        current_app.logger.warning("SUNEDU CSV no encontrado: %s", path)
        return _respuesta_error("csv_no_encontrado")

    grados = []
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            # Normalizar encabezados
            for fila in reader:
                fila_norm = {k.strip().upper(): v.strip() for k, v in fila.items()}
                dni_fila = fila_norm.get("DNI_GRADUADO", "") or fila_norm.get("DNI", "")
                if dni_fila.strip() == dni:
                    grados.append(_normalizar_grado_csv(fila_norm))
    except (OSError, csv.Error) as exc:
        current_app.logger.warning("Error leyendo CSV SUNEDU: %s", exc)
        return _respuesta_error("csv_error_lectura")

    return {
        "fuente": "sunedu",
        "disponible": True,
        "grados": grados,
        "motivo": None,
    }


# ----------------------------------------------------------------
# Normalizadores
# ----------------------------------------------------------------
def _normalizar_grados_api(raw) -> list:
    """Adaptar según la estructura real de la API."""
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = raw.get("grados") or raw.get("titulos") or [raw]
    else:
        return []

    return [_normalizar_grado_dict(item) for item in items if isinstance(item, dict)]


def _normalizar_grado_dict(item: dict) -> dict:
    return {
        "tipo":          item.get("tipoGrado") or item.get("descripcionGrado") or "",
        "denominacion":  item.get("denominacion") or item.get("titulo") or "",
        "universidad":   item.get("universidad") or item.get("nombreUniversidad") or "",
        "fecha":         item.get("fechaExpedicion") or item.get("fechaRegistro") or "",
        "es_bachiller":  _es_bachiller(item),
        "es_titulado":   _es_titulado(item),
        "es_maestria":   _es_maestria(item),
        "es_doctorado":  _es_doctorado(item),
    }


def _normalizar_grado_csv(fila: dict) -> dict:
    grado_raw = fila.get("GRADO_ACADEMICO", "") or fila.get("TIPO_GRADO", "")
    return {
        "tipo":         grado_raw,
        "denominacion": fila.get("DESCRIPCION_GRADO", "") or fila.get("TITULO", ""),
        "universidad":  fila.get("UNIVERSIDAD", "") or fila.get("NOMBRE_UNIVERSIDAD", ""),
        "fecha":        fila.get("FECHA_REGISTRO", "") or fila.get("FECHA_EXPEDICION", ""),
        "es_bachiller": _es_bachiller_str(grado_raw),
        "es_titulado":  _es_titulado_str(grado_raw),
        "es_maestria":  _es_maestria_str(grado_raw),
        "es_doctorado": _es_doctorado_str(grado_raw),
    }


def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", str(texto).lower()).encode("ascii", "ignore").decode()


def _es_bachiller(item: dict) -> bool:
    return _es_bachiller_str(item.get("tipoGrado") or item.get("descripcionGrado") or "")

def _es_titulado(item: dict) -> bool:
    return _es_titulado_str(item.get("tipoGrado") or item.get("descripcionGrado") or "")

def _es_maestria(item: dict) -> bool:
    return _es_maestria_str(item.get("tipoGrado") or item.get("descripcionGrado") or "")

def _es_doctorado(item: dict) -> bool:
    return _es_doctorado_str(item.get("tipoGrado") or item.get("descripcionGrado") or "")

def _es_bachiller_str(s: str) -> bool:
    return "bachiller" in _normalizar(s)

def _es_titulado_str(s: str) -> bool:
    n = _normalizar(s)
    return "titulo" in n or "licenciado" in n or "ingeniero" in n

def _es_maestria_str(s: str) -> bool:
    n = _normalizar(s)
    return "maestria" in n or "magister" in n or "master" in n

def _es_doctorado_str(s: str) -> bool:
    n = _normalizar(s)
    return "doctorado" in n or "doctor" in n or "phd" in n


def _respuesta_error(motivo: str) -> dict:
    return {
        "fuente": "sunedu",
        "disponible": False,
        "grados": [],
        "motivo": motivo,
    }
