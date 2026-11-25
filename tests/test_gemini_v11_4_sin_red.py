"""Pruebas aisladas; ningún secreto ni tráfico a Gemini."""
import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def cargar_backend():
    # Esta prueba se ejecuta incluso en un equipo sin Flask instalado.
    flask = ModuleType('flask')
    flask.current_app = SimpleNamespace(config={'SECRET_KEY': 'clave-de-ensayo-no-real'}, instance_path=tempfile.mkdtemp())
    with patch.dict(sys.modules, {'flask': flask}):
        spec = importlib.util.spec_from_file_location('backend_nexo_test', ROOT/'app/asistente/gemini_backend.py')
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo, flask


def test_denegado_por_defecto():
    m, _ = cargar_backend()
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'TEST_NO_REAL', 'NEXO_GEMINI_HABILITADA':'false'}):
        assert not m.disponible('administrador', True)
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'TEST_NO_REAL', 'NEXO_GEMINI_HABILITADA':'true'}):
        assert not m.disponible('egresado', True)
        assert not m.disponible('publico', False)
        assert m.disponible('administrador', True)


def test_contador_diario_atomico():
    m, _ = cargar_backend()
    with patch.dict('os.environ', {'NEXO_GEMINI_CONSULTAS_DIA': '2'}):
        assert m.consumir_cuota('usuario-prueba')
        assert m.consumir_cuota('usuario-prueba')
        assert not m.consumir_cuota('usuario-prueba')
        assert m.consumir_cuota('otro-usuario')


def test_api_solo_recibe_guia_publica():
    m, _ = cargar_backend()
    red=[]
    class Respuesta:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*a):return json.dumps({'candidates':[{'content':{'parts':[{'text':'GUÍA\n1. Abre tu perfil.\n2. Entra a Mi CV.\n3. Genera tu PDF.'}]}}]}).encode('utf8')

    def urlopen(req, timeout):
        red.append(req)
        assert timeout<=12
        return Respuesta()

    with patch.dict('os.environ', {'GEMINI_API_KEY':'CLAVE_PRUEBA_FALSA'}), patch.object(m.http_request,'urlopen',urlopen):
        salida=m.generar_guia('cv','1. Completa el perfil.\n2. Genera el CV.')
    assert '2. Entra a Mi CV.' in salida
    assert red and red[0].get_header('X-goog-api-key') == 'CLAVE_PRUEBA_FALSA'
    cuerpo=json.loads(red[0].data.decode('utf8'))
    assert cuerpo['generationConfig']['maxOutputTokens']<=320
    assert 'CLAVE_PRUEBA_FALSA' not in red[0].data.decode('utf8')
    assert 'cv' in red[0].data.decode('utf8')


def test_respuesta_sin_pasos_activa_fallback():
    m, _ = cargar_backend()
    class Respuesta:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*a):return json.dumps({'candidates':[{'content':{'parts':[{'text':'Sí, por supuesto.'}]}}]}).encode('utf8')
    with patch.dict('os.environ', {'GEMINI_API_KEY':'CLAVE_PRUEBA_FALSA'}), patch.object(m.http_request,'urlopen',lambda *a,**kw:Respuesta()):
        assert m.generar_guia('cv','contenido verificado') is None
