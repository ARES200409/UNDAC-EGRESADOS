"""Token CSRF puntual para los formularios nuevos V8.
No sustituye protección CSRF global de todos los formularios existentes.
"""
import hmac
import secrets
from flask import session, request, abort


def token_v8():
    token = session.get('nexo_admin_v8_csrf')
    if not token:
        token = secrets.token_urlsafe(32)
        session['nexo_admin_v8_csrf'] = token
    return token


def validar_v8():
    actual = token_v8()
    entregado = request.form.get('_csrf', '')
    if not hmac.compare_digest(actual, entregado):
        abort(400, 'Formulario expirado. Actualiza la página antes de guardar.')
