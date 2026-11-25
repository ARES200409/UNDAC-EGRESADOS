"""Pruebas unitarias del motor de conocimiento (no requieren MySQL)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.asistente.conocimiento import responder_guia

def test_privacidad():
    texto,estado=responder_guia('¿Cuál es la contraseña de un usuario?')
    assert estado=='privacidad'
    assert 'No compartas' in texto

def test_curricula_sin_fecha_inventada():
    texto,_=responder_guia('¿Qué sabes del plan 17A4SI?')
    assert 'pendiente de confirmación' in texto

def test_oferta_no_equivale_a_postular():
    texto,_=responder_guia('¿Cómo puedo postular a una oferta?')
    assert 'Abrir un enlace no equivale a postular' in texto

def test_no_inventa_otros_datos():
    texto,estado=responder_guia('¿Cuál es la nota del estudiante inscrito?')
    assert estado=='sin_coincidencia'
    assert 'contacta al personal autorizado' in texto
