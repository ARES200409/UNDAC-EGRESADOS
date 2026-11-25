# app/api_dni/routes.py
"""Endpoints JSON para el módulo de registro inteligente por DNI.

Rutas:
  GET  /api/dni/<dni>                   → consulta datos del DNI
  POST /api/egresado/<id>/sincronizar   → sincroniza perfil académico
  GET  /api/egresado/<id>/historial     → historial de sincronizaciones

Seguridad:
  - Rate limiting simple por IP (session / in-memory)
  - Consulta DNI solo disponible durante flujo de registro (sesión activa
    de verificación) o autenticado como admin
  - CSRF requerido en POST
  - Nunca se exponen credenciales externas al cliente
"""

import re
from datetime import datetime, timezone
from functools import wraps

from flask import current_app, g, jsonify, request, session
from flask_login import current_user, login_required
from flask_wtf.csrf import validate_csrf

from app.api_dni import api_dni
from app.services.identity_service import consultar_completo
from app.services.academic_sync_service import (
    historial_sync,
    sincronizar_egresado,
)


# ----------------------------------------------------------------
# Helpers de seguridad
# ----------------------------------------------------------------
_RATE_STORE: dict = {}   # ip → {"count": int, "ventana": str (hora)}


def _rate_ok(ip: str, limite: int = 10) -> bool:
    """Limita a `limite` consultas por hora por IP (en memoria).

    Suficiente para el flujo de registro en un único proceso.
    En producción multi-proceso usar Redis o similar.
    """
    hora = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    clave = f"{ip}_{hora}"
    entrada = _RATE_STORE.get(clave, {"count": 0, "ventana": hora})
    if entrada["ventana"] != hora:
        entrada = {"count": 0, "ventana": hora}
    if entrada["count"] >= limite:
        return False
    entrada["count"] += 1
    _RATE_STORE[clave] = entrada
    # Limpiar entradas antiguas cada 100 accesos
    if len(_RATE_STORE) > 500:
        ahora_hora = hora
        claves_viejas = [k for k in _RATE_STORE if not k.endswith(ahora_hora)]
        for k in claves_viejas[:200]:
            _RATE_STORE.pop(k, None)
    return True


def _puede_consultar_dni() -> bool:
    """El endpoint de DNI es accesible si:
    - El usuario está autenticado como admin, o
    - Hay una sesión de registro activa (usuario llegando a /verificar).
    """
    if current_user.is_authenticated and current_user.tiene_rol('administrador'):
        return True
    # Sesión de registro en curso: el usuario aún no tiene cuenta
    if session.get('reg_dni') or session.get('reg_codigo'):
        return True
    # Permitir consulta si la sesión marcó explícitamente la intención
    if session.get('consultando_dni'):
        return True
    return False


def _requiere_admin_o_egresado_propio(id_egresado: int) -> bool:
    """Verifica que el usuario autenticado puede acceder al perfil indicado."""
    if not current_user.is_authenticated:
        return False
    if current_user.tiene_rol('administrador'):
        return True
    if current_user.id_egresado == id_egresado:
        return True
    return False


# ----------------------------------------------------------------
# GET /api/dni/<dni>
# ----------------------------------------------------------------
@api_dni.route('/dni/<string:dni>', methods=['GET'])
def consulta_dni(dni: str):
    """Consulta datos del DNI en fuentes disponibles.

    Accesible durante el flujo de registro (sesión activa) o para admins.
    Rate limit: 10 consultas por hora por IP.

    Respuesta:
      200 { "dni": ..., "encontrado": bool, "estado": ..., "datos_personales": ...,
            "datos_academicos": ..., "grados_titulos": ..., "fuentes": ..., "timestamp": ... }
      400 { "error": "dni_invalido" }
      429 { "error": "limite_excedido" }
      403 { "error": "acceso_denegado" }
    """
    # Limpiar DNI
    dni = re.sub(r'\D', '', str(dni or ''))

    if len(dni) != 8:
        return jsonify({"error": "dni_invalido", "mensaje": "El DNI debe tener 8 dígitos."}), 400

    # Control de acceso
    if not _puede_consultar_dni():
        return jsonify({"error": "acceso_denegado", "mensaje": "Inicia el proceso de registro o autentícate."}), 403

    # Rate limiting
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr or '').split(',')[0].strip()
    limite = int(current_app.config.get('DNI_LOOKUP_RATE_LIMIT', 10))
    if not _rate_ok(ip, limite):
        return jsonify({"error": "limite_excedido", "mensaje": "Demasiadas consultas. Espera un momento."}), 429

    # Marcar intención en sesión
    session['consultando_dni'] = True

    # Consultar fuentes
    resultado = consultar_completo(dni)
    return jsonify(resultado), 200


# ----------------------------------------------------------------
# POST /api/egresado/<id>/sincronizar
# ----------------------------------------------------------------
@api_dni.route('/egresado/<int:id_egresado>/sincronizar', methods=['POST'])
@login_required
def sincronizar(id_egresado: int):
    """Sincroniza el perfil académico de un egresado con fuentes externas.

    Requiere autenticación. Solo el propio egresado o un admin puede ejecutarlo.
    Requiere CSRF.

    Respuesta:
      200 { "ok": true, "cambios": [ ... ] }
      403 { "error": "acceso_denegado" }
    """
    # Verificar CSRF en AJAX
    token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token', '')
    try:
        validate_csrf(token)
    except Exception:
        return jsonify({"error": "csrf_invalido"}), 400

    if not _requiere_admin_o_egresado_propio(id_egresado):
        return jsonify({"error": "acceso_denegado"}), 403

    operador = "admin" if current_user.tiene_rol('administrador') else "egresado"
    resultado = sincronizar_egresado(id_egresado, operador=operador)

    return jsonify(resultado), 200 if resultado["ok"] else 500


# ----------------------------------------------------------------
# GET /api/egresado/<id>/historial
# ----------------------------------------------------------------
@api_dni.route('/egresado/<int:id_egresado>/historial', methods=['GET'])
@login_required
def ver_historial(id_egresado: int):
    """Retorna el historial de sincronizaciones del egresado.

    Respuesta:
      200 { "historial": [ { ... } ] }
      403 { "error": "acceso_denegado" }
    """
    if not _requiere_admin_o_egresado_propio(id_egresado):
        return jsonify({"error": "acceso_denegado"}), 403

    limite = min(int(request.args.get('limite', 50)), 200)
    entradas = historial_sync(id_egresado, limite=limite)
    return jsonify({"historial": entradas}), 200
