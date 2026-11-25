# app/services/identity_service.py
"""Orquestador de identidad y datos académicos para NEXO UNDAC.

Coordina las consultas a UNDAC API, RENIEC y SUNEDU,
consolida los resultados y etiqueta la procedencia de cada campo.

No expone credenciales al cliente: todo el procesamiento ocurre
en el servidor; el endpoint retorna JSON ya consolidado.
"""

from datetime import datetime, timezone

from app.services.reniec_service import consultar_reniec
from app.services.sunedu_service import consultar_sunedu
from app.services.undac_academic_service import buscar_por_dni


# ----------------------------------------------------------------
# Función principal
# ----------------------------------------------------------------
def consultar_completo(dni: str) -> dict:
    """Consulta todas las fuentes disponibles y consolida la respuesta.

    Retorna:
    {
        "dni": str,
        "encontrado": bool,
        "estado": "encontrado" | "parcial" | "sin_datos",
        "datos_personales": { campo: { "valor": ..., "fuente": ... } },
        "datos_academicos": { campo: { "valor": ..., "fuente": ... } },
        "grados_titulos":   [ { ... } ],
        "fuentes": {
            "undac_api": { "disponible": bool, "motivo": str|None },
            "reniec":    { "disponible": bool, "motivo": str|None },
            "sunedu":    { "disponible": bool, "motivo": str|None }
        },
        "timestamp": str (ISO 8601)
    }
    """
    dni = str(dni or "").strip()

    if not dni.isdigit() or len(dni) != 8:
        return {
            "dni": dni,
            "encontrado": False,
            "estado": "dni_invalido",
            "datos_personales": {},
            "datos_academicos": {},
            "grados_titulos": [],
            "fuentes": {},
            "timestamp": _now_iso(),
        }

    # ── Consultar fuentes en secuencia (UNDAC → RENIEC → SUNEDU) ──
    r_undac  = buscar_por_dni(dni)
    r_reniec = consultar_reniec(dni)
    r_sunedu = consultar_sunedu(dni)

    # ── Consolidar datos personales ──
    personales = _consolidar_personales(r_undac, r_reniec)

    # ── Consolidar datos académicos ──
    academicos = _consolidar_academicos(r_undac, r_sunedu)

    # ── Lista de grados y títulos ──
    grados = r_sunedu.get("grados", [])

    # ── Estado global ──
    hay_datos_personales = any(
        v.get("valor") for v in personales.values()
    )
    encontrado = hay_datos_personales or bool(r_undac["disponible"])

    if r_undac["disponible"] and hay_datos_personales:
        estado = "encontrado"
    elif encontrado:
        estado = "parcial"
    else:
        estado = "sin_datos"

    return {
        "dni": dni,
        "encontrado": encontrado,
        "estado": estado,
        "datos_personales": personales,
        "datos_academicos": academicos,
        "grados_titulos": grados,
        "fuentes": {
            "undac_api": {
                "disponible": r_undac["disponible"],
                "motivo":     r_undac.get("motivo"),
            },
            "reniec": {
                "disponible": r_reniec["disponible"],
                "motivo":     r_reniec.get("motivo"),
            },
            "sunedu": {
                "disponible": r_sunedu["disponible"],
                "motivo":     r_sunedu.get("motivo"),
            },
        },
        "timestamp": _now_iso(),
    }


# ----------------------------------------------------------------
# Consolidadores
# ----------------------------------------------------------------
_CAMPOS_PERSONALES = [
    "nombres", "apellido_paterno", "apellido_materno",
    "fecha_nacimiento", "genero",
]

_CAMPOS_ACADEMICOS = [
    "codigo_universitario", "curricula", "programa_facultad",
    "id_escuela", "anio_ingreso", "domicilio",
    "correo_institucional",
    # Flags de grados (vendrán de SUNEDU si hay grados)
    "es_bachiller", "es_titulado", "tiene_maestria", "tiene_doctorado",
]


def _consolidar_personales(r_undac: dict, r_reniec: dict) -> dict:
    """Prioridad: RENIEC > UNDAC_API (para datos personales)."""
    resultado = {}

    datos_undac  = r_undac.get("datos") or {}
    datos_reniec = r_reniec.get("datos") or {}

    for campo in _CAMPOS_PERSONALES:
        val_reniec = datos_reniec.get(campo, "")
        val_undac  = datos_undac.get(campo, "")

        if val_reniec:
            resultado[campo] = {"valor": val_reniec, "fuente": "reniec"}
        elif val_undac:
            resultado[campo] = {"valor": str(val_undac), "fuente": "undac_api"}
        else:
            resultado[campo] = {"valor": "", "fuente": "sin_datos"}

    return resultado


def _consolidar_academicos(r_undac: dict, r_sunedu: dict) -> dict:
    """Prioridad: UNDAC_API > SUNEDU (para datos académicos)."""
    resultado = {}

    datos_undac = r_undac.get("datos") or {}
    grados      = r_sunedu.get("grados") or []

    for campo in _CAMPOS_ACADEMICOS:
        val_undac = datos_undac.get(campo, "")

        if val_undac not in (None, "", 0):
            resultado[campo] = {"valor": str(val_undac), "fuente": "undac_api"}
        else:
            # Intentar derivar de grados SUNEDU
            val_sunedu = _derivar_de_grados(campo, grados)
            if val_sunedu is not None:
                resultado[campo] = {"valor": val_sunedu, "fuente": "sunedu"}
            else:
                resultado[campo] = {"valor": "", "fuente": "sin_datos"}

    return resultado


def _derivar_de_grados(campo: str, grados: list):
    """Deriva valores booleanos de grados de la lista de SUNEDU."""
    if not grados:
        return None

    mapa = {
        "es_bachiller":  any(g.get("es_bachiller")  for g in grados),
        "es_titulado":   any(g.get("es_titulado")   for g in grados),
        "tiene_maestria": any(g.get("es_maestria")  for g in grados),
        "tiene_doctorado": any(g.get("es_doctorado") for g in grados),
    }
    if campo in mapa:
        return "1" if mapa[campo] else None
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
