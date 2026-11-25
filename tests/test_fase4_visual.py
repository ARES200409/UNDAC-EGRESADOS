"""Pruebas de la Fase 4: diseño visual, CSS por rol y compilación de plantillas Jinja2."""

import os
import pytest
from config import Config
from app import create_app


@pytest.fixture
def app_visual(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase4-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    app = create_app()
    with app.app_context():
        yield app


def test_todas_las_plantillas_jinja_compilan(app_visual):
    plantillas = app_visual.jinja_env.list_templates()
    assert len(plantillas) >= 60
    for nombre in plantillas:
        app_visual.jinja_env.get_template(nombre)


def test_css_roles_v12_existe_y_esta_enlazado(app_visual):
    ruta_css = os.path.join(app_visual.static_folder, 'css', 'nexo_roles_v12.css')
    assert os.path.isfile(ruta_css)
    contenido, _, _ = app_visual.jinja_loader.get_source(app_visual.jinja_env, 'base.html')
    assert 'nexo_roles_v12.css' in contenido
    assert '_nav_por_rol.html' in contenido
