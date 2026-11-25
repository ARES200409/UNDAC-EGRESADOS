"""Validación estática offline V11.5; no prueba MySQL, Gemini ni Chrome."""
from pathlib import Path
import ast
import importlib.util
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
REQUIRED=[
    'app/static/js/nexo_chat.js',
    'app/static/css/nexo_chat.css',
    'app/templates/includes/_nexo_asistente.html',
    'app/asistente/routes.py',
    'app/asistente/conocimiento.py',
]
errors=[]
for filename in REQUIRED:
    f=ROOT/filename
    if f.is_file():print('[OK]',filename)
    else:errors.append('Falta '+filename)
if not errors:
    js=(ROOT/REQUIRED[0]).read_text(encoding='utf-8')
    css=(ROOT/REQUIRED[1]).read_text(encoding='utf-8')
    html=(ROOT/REQUIRED[2]).read_text(encoding='utf-8')
    for name in re.findall(r"\$\('([\w-]+)'\)",js):
        if not re.search(r'\bid=["\']'+re.escape(name)+r'["\']', html):
            errors.append('Selector JS inexistente en HTML: '+name)
    for token in ('nexo-chat-new','nexo-chat-history-toggle','nexo-chat-clear','nexo-chat-save','nexo-chat-export','nexo-chat-expand'):
        if token not in html:errors.append('Falta herramienta: '+token)
    if 'saveEnabled = false' not in js:
        errors.append('Historial debe iniciar desactivado')
    for key in ('nexo-chat-wide','nexo-chat-history','@media(max-width:650px)'):
        if key not in css:errors.append('Falta estilo: '+key)
    for filename in REQUIRED[-2:]:
        try:ast.parse((ROOT/filename).read_text(encoding='utf-8'))
        except SyntaxError as ex:errors.append('Error Python '+filename+': '+str(ex))
    try:
        from jinja2 import Environment
        Environment().parse(html)
        print('[OK] Jinja compilado')
    except ImportError:
        print('[INFO] Jinja no instalado; solo se verificaron selectores')
    except Exception as ex:
        errors.append('Jinja: '+str(ex))
    if shutil.which('node'):
        result=subprocess.run(['node','--check',str(ROOT/REQUIRED[0])],capture_output=True,text=True)
        if result.returncode:errors.append('JS: '+result.stderr[:350])
        else:print('[OK] Sintaxis JavaScript')
    else: print('[INFO] Node no disponible; no se compiló JavaScript')
    spec=importlib.util.spec_from_file_location('nexo_conocimiento_prueba',str(ROOT/'app/asistente/conocimiento.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    guia, categoria = module.responder_guia('¿Cómo genero mi CV?')
    assert 'GENERAR TU CV' in guia and categoria=='guia'
    paso = module.explicar_paso('Explícame el paso 3','cv')
    assert 'PASO 3' in paso and 'Registra' in paso, paso
    assert module.explicar_paso('Explícame el paso 3','tema_no_permitido') is None
    assert module.explicar_paso('¿Cómo genero mi CV?','cv') is None
    print('[OK] Guía contextual: CV, paso 3, temas no autorizados')
print('[RESULTADO]', 'REVISIÓN ESTÁTICA CORRECTA' if not errors else 'ERRORES: '+str(len(errors)))
for e in errors:print('[ERROR]',e)
print('[NOTA] No prueba Flask/MySQL, navegador ni Gemini; hay que comprobarlo en el equipo destino.')
sys.exit(bool(errors))
