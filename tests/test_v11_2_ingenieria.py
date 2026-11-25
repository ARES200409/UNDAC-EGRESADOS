"""Pruebas de robustez sin escribir en MySQL, usan SQLite en memoria."""
import json
import pytest
from sqlalchemy.exc import OperationalError
from config import Config
from app import create_app
import app.ops_v11_2 as operaciones

@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-de-test-no-usar-en-produccion-2026', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)
    aplicacion=create_app()
    with aplicacion.test_client() as client:
        yield client

def test_liveness_y_readiness(cliente):
    assert cliente.get('/health/live').json == {'service':'nexo-undac','status':'ok'}
    respuesta=cliente.get('/health/ready')
    assert respuesta.status_code==200
    assert respuesta.json['status']=='ready'

def test_readiness_503_sin_exponer_credenciales(cliente,monkeypatch):
    def fallar(): raise OperationalError('SELECT 1',{},Exception('desconectado'))
    monkeypatch.setattr(operaciones,'_comprobar_db',fallar)
    r=cliente.get('/health/ready')
    assert r.status_code==503
    assert r.json == {'service':'nexo-undac','status':'unavailable'}
    assert 'SELECT' not in r.get_data(as_text=True)

def test_cabeceras_y_correlacion_de_peticiones(cliente):
    a=cliente.get('/health/live');b=cliente.get('/health/live')
    assert len(a.headers['X-Request-ID']) == 16
    assert a.headers['X-Request-ID'] != b.headers['X-Request-ID']
    assert a.headers['X-Content-Type-Options']=='nosniff'
    assert 'no-store' in a.headers['Cache-Control']

def test_api_institucional_no_se_expone_sin_sesion(cliente):
    r=cliente.get('/admin/api/v11/indicadores',follow_redirects=False)
    assert r.status_code in (302,401,403)

def test_trazas_no_incluyen_querystrings(cliente,caplog):
    caplog.set_level('INFO')
    cliente.get('/health/live?dni=NO-DEBE-APARECER&correo=PRIVADO')
    mensajes='\n'.join(r.message for r in caplog.records)
    assert 'NO-DEBE-APARECER' not in mensajes
    assert 'PRIVADO' not in mensajes
