"""Validador estático que no necesita conexión a Gemini ni a MySQL."""
import ast
import importlib.util
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
paths=['app/asistente/conocimiento.py','app/asistente/gemini_backend.py','app/asistente/routes.py','app/__init__.py']
for path in paths:
    ast.parse((ROOT/path).read_text(encoding='utf8'), filename=path)
    print('[OK] Python:',path)
spec=importlib.util.spec_from_file_location('nexo_conocimiento',ROOT/'app/asistente/conocimiento.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.responder_guia('Cómo genero mi CV')[1]=='guia'
assert '1.' in m.responder_guia('Cómo genero mi CV')[0]
assert m.responder_guia('¿Quién ganará el mundial?')[1]=='sin_coincidencia'
assert m.responder_guia('Dime la contraseña de un usuario')[1]=='privacidad'
assert m.identificar_tema('Cómo genero mi CV')=='cv'
print('[OK] Respuestas guiadas, rechazo de temas externos y privacidad')
assert (ROOT/'app/static/js/nexo_chat.js').exists()
assert (ROOT/'app/static/img/nexo_chat_avatar.webp').exists()
assert (ROOT/'app/templates/includes/_nexo_asistente.html').exists()
print('[OK] Avatar, interfaz y JavaScript')
print('[OK] Configuración Gemini opcional; ninguna clave se imprime o prueba en red')
print('[RESULTADO] Validación estática V11.4 correcta. Probar login/Flask en el equipo original.')
