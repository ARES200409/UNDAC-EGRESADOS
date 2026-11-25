# app/services/reniec_service.py
"""Adaptador RENIEC para NEXO UNDAC.

IMPORTANTE: RENIEC no dispone de API pública gratuita.
La consulta real requiere convenio institucional con RENIEC
(Resolución Jefatural o contrato de servicio).

Mientras la UNDAC no tenga credenciales activas, este módulo
devuelve siempre {"disponible": False, "fuente": "reniec",
"motivo": "sin_credenciales"} sin realizar ninguna solicitud externa.

Cuando se obtengan las credenciales, configurar en .env:
  RENIEC_API_URL=https://api.reniec.gob.pe/...
  RENIEC_API_KEY=<clave_institucional>

Referencia oficial:
  https://www.reniec.gob.pe/portal/serviciosLinea.htm
  https://www.gob.pe/institucion/reniec/colecciones/3049-servicios-en-linea
"""

import os
import requests
from flask import current_app


# ----------------------------------------------------------------
# Configuración (leída al momento de la llamada para permitir
# cambios en .env sin reiniciar en desarrollo)
# ----------------------------------------------------------------
def _config():
    return {
        "url": os.getenv("RENIEC_API_URL", "").strip(),
        "key": os.getenv("RENIEC_API_KEY", "").strip(),
    }


def _credenciales_ok():
    cfg = _config()
    return bool(cfg["url"] and cfg["key"])


# ----------------------------------------------------------------
# Función principal
# ----------------------------------------------------------------
def consultar_reniec(dni: str) -> dict:
    """Consulta datos personales por DNI en la API de RENIEC.

    Retorna un diccionario con la estructura:
    {
        "fuente": "reniec",
        "disponible": True | False,
        "datos": { ... } | None,
        "motivo": str | None      # solo cuando disponible=False
    }

    Nunca lanza excepciones: errores de red o configuración
    se devuelven como disponible=False con el motivo indicado.
    """
    dni = str(dni or "").strip()

    # Validación básica de DNI
    if not dni.isdigit() or len(dni) != 8:
        return {
            "fuente": "reniec",
            "disponible": False,
            "datos": None,
            "motivo": "dni_invalido",
        }

    # Sin credenciales → retorno inmediato, sin consultas externas
    if not _credenciales_ok():
        return {
            "fuente": "reniec",
            "disponible": False,
            "datos": None,
            "motivo": "sin_credenciales",
        }

    cfg = _config()
    try:
        respuesta = requests.get(
            f"{cfg['url']}/{dni}",
            headers={
                "Authorization": f"Bearer {cfg['key']}",
                "Accept": "application/json",
            },
            timeout=(5, 10),
        )

        if respuesta.status_code == 200:
            datos_raw = respuesta.json()
            # Normalizar al esquema interno
            datos = _normalizar_respuesta(datos_raw)
            return {
                "fuente": "reniec",
                "disponible": True,
                "datos": datos,
                "motivo": None,
            }

        if respuesta.status_code == 404:
            return {
                "fuente": "reniec",
                "disponible": True,
                "datos": None,
                "motivo": "dni_no_encontrado",
            }

        return {
            "fuente": "reniec",
            "disponible": False,
            "datos": None,
            "motivo": f"http_{respuesta.status_code}",
        }

    except requests.exceptions.Timeout:
        return {
            "fuente": "reniec",
            "disponible": False,
            "datos": None,
            "motivo": "timeout",
        }
    except requests.exceptions.ConnectionError:
        return {
            "fuente": "reniec",
            "disponible": False,
            "datos": None,
            "motivo": "conexion_fallida",
        }
    except (requests.exceptions.RequestException, ValueError) as exc:
        current_app.logger.warning("RENIEC service error: %s", exc)
        return {
            "fuente": "reniec",
            "disponible": False,
            "datos": None,
            "motivo": "error_inesperado",
        }


# ----------------------------------------------------------------
# Normalización de respuesta (adaptar según la API real)
# ----------------------------------------------------------------
def _normalizar_respuesta(raw: dict) -> dict:
    """Convierte la respuesta de RENIEC al esquema interno de NEXO.

    Los nombres de campos son orientativos; ajustar cuando se
    conozca la estructura real de la API contratada.
    """
    if not isinstance(raw, dict):
        return {}

    return {
        "nombres":          raw.get("nombres") or raw.get("primerNombre") or "",
        "apellido_paterno": raw.get("apellidoPaterno") or raw.get("apPaterno") or "",
        "apellido_materno": raw.get("apellidoMaterno") or raw.get("apMaterno") or "",
        "fecha_nacimiento": raw.get("fechaNacimiento") or raw.get("fecNacimiento") or "",
        "genero":           _normalizar_genero(raw.get("sexo") or raw.get("genero") or ""),
        "ubigeo_nacimiento": raw.get("ubigeoNacimiento") or "",
    }


def _normalizar_genero(valor: str) -> str:
    v = str(valor).upper().strip()
    if v in ("M", "MASCULINO", "MALE"):
        return "M"
    if v in ("F", "FEMENINO", "FEMALE"):
        return "F"
    return ""
