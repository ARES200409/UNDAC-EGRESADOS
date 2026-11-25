"""Pruebas no destructivas: usan SQLite en memoria, no tu base MySQL local."""
import pytest
from config import Config
from app import create_app
from app.ambito import normalizar, es_programa_sistemas


def test_nombre_programa_exactamente_sistemas():
    assert es_programa_sistemas('Ingeniería de Sistemas y Computación')
    assert es_programa_sistemas('  INGENIERIA DE SISTEMAS Y COMPUTACION ')
    assert not es_programa_sistemas('Ciencias Sociales, Filosofía y Psicología Educativa')


def test_normalizacion_acentos():
    assert normalizar('Ingeniería') == normalizar('Ingenieria')


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-prueba-solo-test-no-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)
    app = create_app()
    with app.test_client() as cliente:
        yield cliente


def test_api_indicadores_no_publica(client):
    response = client.get('/admin/api/v11/indicadores')
    assert response.status_code in (302, 401, 403)
    assert 'X-Content-Type-Options' in response.headers


def test_cabeceras_de_seguridad(client):
    response = client.get('/ruta-inexistente')
    assert response.status_code == 404
    assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert 'no-store' in response.headers['Cache-Control']
