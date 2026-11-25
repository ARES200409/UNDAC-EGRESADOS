# app/services/undac_academic_service.py
"""Adaptador para la API académica interna de la UNDAC.

Envuelve helpers.consultar_api() añadiendo:
  - Búsqueda por DNI (vía BD local → código → API)
  - Normalización de respuesta al esquema interno
  - Graceful fallback si la API no responde
"""

from datetime import datetime

from app.helpers import consultar_api, datos_api_a_egresado


# ----------------------------------------------------------------
# Búsqueda por DNI
# ----------------------------------------------------------------
def buscar_por_dni(dni: str) -> dict:
    """Busca datos académicos a partir del DNI.

    Estrategia:
      1. Busca el egresado en la BD local por DNI para obtener
         su código universitario.
      2. Si tiene código, consulta la API UNDAC.
      3. Si no está en BD o la API falla, retorna disponible=False.

    Retorna:
    {
        "fuente": "undac_api",
        "disponible": True | False,
        "datos": { ... } | None,
        "motivo": str | None
    }
    """
    # Import dentro de la función para evitar ciclos circulares
    from app.models import Egresados

    dni = str(dni or "").strip()
    if not dni.isdigit() or len(dni) != 8:
        return _error("dni_invalido")

    # Paso 1: buscar en BD local
    egresado = Egresados.query.filter_by(dni=dni).first()
    codigo = egresado.codigo_universitario if egresado else None

    if not codigo:
        return _error("codigo_no_encontrado")

    # Paso 2: consultar API UNDAC
    return buscar_por_codigo(codigo)


def buscar_por_codigo(codigo_universitario: str) -> dict:
    """Consulta la API UNDAC por código universitario.

    Retorna el mismo esquema que buscar_por_dni().
    """
    codigo = str(codigo_universitario or "").strip()
    if not codigo:
        return _error("codigo_vacio")

    datos_raw = consultar_api(codigo)
    if datos_raw is None:
        return _error("api_sin_respuesta")

    # Validar que el Rol sea EG (egresado)
    if datos_raw.get("Rol") != "EG":
        return _error("rol_no_egresado")

    datos = _normalizar(datos_raw)
    return {
        "fuente": "undac_api",
        "disponible": True,
        "datos": datos,
        "motivo": None,
    }


# ----------------------------------------------------------------
# Verificación de código + DNI (flujo actual de /verificar)
# ----------------------------------------------------------------
def verificar_codigo_y_dni(codigo: str, dni: str) -> dict:
    """Verifica que el código corresponde al DNI en la API UNDAC.

    Mantiene el flujo actual del formulario de verificación para
    compatibilidad hacia atrás.

    Retorna:
    {
        "valido": True | False,
        "datos": { ... } | None,
        "error": str | None
    }
    """
    resultado = buscar_por_codigo(codigo)
    if not resultado["disponible"]:
        return {"valido": False, "datos": None, "error": resultado["motivo"]}

    datos = resultado["datos"]
    if datos.get("dni", "").strip() != str(dni or "").strip():
        return {"valido": False, "datos": None, "error": "dni_no_coincide"}

    return {"valido": True, "datos": datos, "error": None}


# ----------------------------------------------------------------
# Normalización interna
# ----------------------------------------------------------------
def _normalizar(raw: dict) -> dict:
    """Convierte la respuesta de la API al esquema interno."""
    base = datos_api_a_egresado(raw)

    # Enriquecer con campos adicionales que devuelve la API
    return {
        **base,
        "codigo_universitario": str(raw.get("Codigo", "") or "").strip(),
        "curricula":            str(raw.get("Curricula", "") or "").strip(),
        "programa_facultad":    str(raw.get("Programa facultad", "") or "").strip(),
        "id_escuela":           str(raw.get("ID_ESCUELA", "") or "").strip(),
        "rol":                  str(raw.get("Rol", "") or "").strip(),
    }


def _error(motivo: str) -> dict:
    return {
        "fuente": "undac_api",
        "disponible": False,
        "datos": None,
        "motivo": motivo,
    }
