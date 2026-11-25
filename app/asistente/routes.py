"""Asistente NEXO: reglas verificadas + Gemini exclusivo de personal autorizado."""
import time
from collections import defaultdict, deque
from threading import Lock
from flask import jsonify, request, current_app
from flask_login import current_user
from app.asistente import asistente
from app.asistente.conocimiento import responder_guia, identificar_tema, explicar_paso
from app.asistente.gemini_backend import disponible, consumir_cuota, generar_guia

_POR_MINUTO = defaultdict(deque)
_CERROJO = Lock()


def _rol():
    return (current_user.rol_activo_nombre() or 'publico') if current_user.is_authenticated else 'publico'


def limites_autorizados():
    llave = ('u:' + str(current_user.get_id())) if current_user.is_authenticated else ('ip:' + str(request.remote_addr or 'unknown'))
    ahora = time.monotonic()
    with _CERROJO:
        if len(_POR_MINUTO) > 1500:
            for k in list(_POR_MINUTO):
                if not _POR_MINUTO[k] or ahora - _POR_MINUTO[k][-1] > 60:
                    del _POR_MINUTO[k]
        q = _POR_MINUTO[llave]
        while q and ahora - q[0] > 60:
            q.popleft()
        if len(q) >= 10:
            return False
        q.append(ahora)
    return True


@asistente.get('/api/estado')
def estado():
    rol = _rol()
    return jsonify(guia=True, ia_habilitada=disponible(rol, current_user.is_authenticated), max_caracteres=300)


@asistente.post('/api/mensaje')
def mensaje():
    if not limites_autorizados():
        return jsonify(error='Límite de 10 consultas por minuto. Prueba de nuevo más tarde.'), 429
    if not request.is_json:
        return jsonify(error='Envía una consulta JSON.'), 415
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error='Consulta no válida.'), 400
    pregunta = datos.get('mensaje')
    if not isinstance(pregunta, str) or not 2 <= len(pregunta.strip()) <= 300:
        return jsonify(error='Escribe una pregunta de 2 a 300 caracteres.'), 400
    rol = _rol()
    contexto = datos.get('contexto_tema', '')
    # Un seguimiento como «Explícame el paso 3» reutiliza solo el tema verificado.
    # El cliente nunca puede solicitar temas fuera del catálogo público aprobado.
    guia_paso = explicar_paso(pregunta, contexto)
    if guia_paso is not None:
        return jsonify(respuesta=guia_paso, modo='guia', categoria='paso', tema=contexto)
    guia, categoria = responder_guia(pregunta, rol)
    tema = identificar_tema(pregunta)
    respuesta_local = dict(respuesta=guia, modo='guia', categoria=categoria, tema=tema)
    # Filtro: si no hay tema específico o hay datos sensibles, NUNCA salir a Internet.
    if categoria in {'privacidad', 'sin_coincidencia', 'ayuda'}:
        return jsonify(respuesta_local)
    if not tema or tema == 'saludo':
        return jsonify(respuesta_local)
    # Modo IA exclusivamente para personal autorizado y consentimiento explícito.
    if not (datos.get('usar_ia') is True and datos.get('consentimiento') is True
            and disponible(rol, current_user.is_authenticated)):
        return jsonify(respuesta_local)
    try:
        if not consumir_cuota(current_user.get_id()):
            respuesta_local['aviso'] = 'Se alcanzó el cupo diario de IA; disponible la guía local.'
            return jsonify(respuesta_local)
        # Al proveedor solo se transmite el tema y la guía pública autorizada,
        # nunca el texto original escrito por el usuario ni registros personales.
        generado = generar_guia(tema, guia)
        if generado:
            return jsonify(respuesta=generado, modo='ia', categoria=categoria, tema=tema)
    except Exception:
        current_app.logger.warning('NEXO IA: fallo proveedor, respuesta de respaldo activada; sin registrar datos privados')
    respuesta_local['aviso'] = 'Servicio de IA no disponible; se mostró la guía institucional.'
    return jsonify(respuesta_local)
