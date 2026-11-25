"""Trazas JSON sin cuerpos, URL con consultas, correo, IP ni datos personales."""
import json
import time
from uuid import uuid4
from flask import g, request

def registrar_observabilidad(app):
    @app.before_request
    def _inicio_peticion_v11_2():
        g._nexo_request_id = uuid4().hex[:16]
        g._nexo_inicio = time.perf_counter()

    @app.after_request
    def _fin_peticion_v11_2(respuesta):
        identificador = getattr(g, '_nexo_request_id', uuid4().hex[:16])
        respuesta.headers['X-Request-ID'] = identificador
        if request.path.startswith('/static/'):
            return respuesta
        duracion = (time.perf_counter() - getattr(g, '_nexo_inicio', time.perf_counter())) * 1000
        registro = {
            'evento': 'http_request',
            'id': identificador,
            'metodo': request.method,
            'endpoint': request.endpoint or 'sin_ruta',
            'estado_http': respuesta.status_code,
            'ms': round(duracion, 1),
        }
        app.logger.info(json.dumps(registro, ensure_ascii=False, separators=(',', ':')))
        return respuesta
