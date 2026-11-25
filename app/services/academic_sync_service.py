# app/services/academic_sync_service.py
"""Servicio de sincronización académica para NEXO UNDAC.

Gestiona la actualización del perfil académico de un egresado
a partir de las fuentes externas (SUNEDU, RENIEC, UNDAC API),
registrando cada cambio en historial_sync_academico.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models import Egresados, HistorialSyncAcademico
from app.services.identity_service import consultar_completo


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ----------------------------------------------------------------
# Sincronizar egresado individual
# ----------------------------------------------------------------
def sincronizar_egresado(id_egresado: int, operador: str = "sistema") -> dict:
    """Consulta fuentes externas y actualiza el perfil del egresado.

    Parámetros:
      id_egresado: PK del egresado a sincronizar.
      operador: 'sistema' | 'egresado' | 'admin'

    Retorna:
    {
        "ok": bool,
        "cambios": [ { "campo": ..., "anterior": ..., "nuevo": ..., "fuente": ... } ],
        "error": str | None
    }
    """
    egresado = db.session.get(Egresados, id_egresado)
    if not egresado:
        return {"ok": False, "cambios": [], "error": "egresado_no_encontrado"}

    resultado = consultar_completo(egresado.dni)
    if not resultado.get("encontrado"):
        return {
            "ok": True,
            "cambios": [],
            "error": None,
        }

    cambios = []
    datos_p = resultado.get("datos_personales", {})
    datos_a = resultado.get("datos_academicos", {})
    grados  = resultado.get("grados_titulos", [])

    # Mapa campo_modelo → (nuevo_valor, fuente)
    actualizaciones = {}

    # Campos personales (solo actualizar si RENIEC lo provee)
    for campo in ["nombres", "apellido_paterno", "apellido_materno",
                  "fecha_nacimiento", "genero"]:
        info = datos_p.get(campo, {})
        if info.get("fuente") == "reniec" and info.get("valor"):
            actualizaciones[campo] = (info["valor"], "reniec")

    # Campos académicos
    for campo in ["codigo_universitario", "anio_ingreso"]:
        info = datos_a.get(campo, {})
        if info.get("fuente") == "undac_api" and info.get("valor"):
            actualizaciones[campo] = (info["valor"], "undac_api")

    # Grados y títulos de SUNEDU
    if grados:
        nuevos_flags = {
            "es_bachiller":    1 if any(g.get("es_bachiller")  for g in grados) else None,
            "es_titulado":     1 if any(g.get("es_titulado")   for g in grados) else None,
            "tiene_maestria":  1 if any(g.get("es_maestria")   for g in grados) else None,
            "tiene_doctorado": 1 if any(g.get("es_doctorado")  for g in grados) else None,
        }
        for campo, nuevo_val in nuevos_flags.items():
            if nuevo_val is not None:
                actualizaciones[campo] = (nuevo_val, "sunedu")

    # Aplicar actualizaciones y registrar historial
    for campo, (nuevo_val, fuente) in actualizaciones.items():
        valor_actual = getattr(egresado, campo, None)
        # Convertir para comparación homogénea
        actual_str = str(valor_actual) if valor_actual is not None else ""
        nuevo_str  = str(nuevo_val)

        if actual_str == nuevo_str:
            continue  # Sin cambio real

        # Registrar en historial
        entrada = HistorialSyncAcademico(
            id_egresado    = id_egresado,
            fuente         = fuente,
            campo          = campo,
            valor_anterior = actual_str or None,
            valor_nuevo    = nuevo_str,
            operador       = operador,
            creado_en      = _utc_now(),
        )
        db.session.add(entrada)

        # Actualizar modelo
        setattr(egresado, campo, nuevo_val)

        cambios.append({
            "campo":    campo,
            "anterior": actual_str or None,
            "nuevo":    nuevo_str,
            "fuente":   fuente,
        })

    # Actualizar timestamps de última sync
    ahora = _utc_now()
    fuentes_consultadas = resultado.get("fuentes", {})
    if fuentes_consultadas.get("undac_api", {}).get("disponible"):
        egresado.ultima_sync_undac = ahora
    if fuentes_consultadas.get("reniec", {}).get("disponible"):
        egresado.ultima_sync_reniec = ahora
    if fuentes_consultadas.get("sunedu", {}).get("disponible"):
        egresado.ultima_sync_sunedu = ahora

    # Recalcular nivel máximo si hubo cambios en flags
    if any(c["campo"] in ("es_bachiller","es_titulado","tiene_maestria","tiene_doctorado")
           for c in cambios):
        egresado.actualizar_nivel_maximo()

    db.session.commit()

    return {"ok": True, "cambios": cambios, "error": None}


# ----------------------------------------------------------------
# Historial de un egresado
# ----------------------------------------------------------------
def historial_sync(id_egresado: int, limite: int = 50) -> list:
    """Devuelve las últimas N entradas del historial de sincronización."""
    entradas = (
        HistorialSyncAcademico.query
        .filter_by(id_egresado=id_egresado)
        .order_by(HistorialSyncAcademico.creado_en.desc())
        .limit(limite)
        .all()
    )
    return [
        {
            "id_sync":        e.id_sync,
            "fuente":         e.fuente,
            "campo":          e.campo,
            "valor_anterior": e.valor_anterior,
            "valor_nuevo":    e.valor_nuevo,
            "operador":       e.operador,
            "creado_en":      e.creado_en.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for e in entradas
    ]


# ----------------------------------------------------------------
# Registrar cambio manual
# ----------------------------------------------------------------
def registrar_cambio_manual(id_egresado: int, campo: str,
                             valor_anterior, valor_nuevo,
                             operador: str = "admin") -> None:
    """Registra un cambio realizado manualmente (sin sincronización automática)."""
    entrada = HistorialSyncAcademico(
        id_egresado    = id_egresado,
        fuente         = "manual",
        campo          = campo,
        valor_anterior = str(valor_anterior) if valor_anterior is not None else None,
        valor_nuevo    = str(valor_nuevo) if valor_nuevo is not None else None,
        operador       = operador,
        creado_en      = _utc_now(),
    )
    db.session.add(entrada)
    db.session.commit()
