"""Pruebas unitarias de la Fase 2: arquitectura, almacenamiento privado y validaciones."""

import io
import os
from datetime import date
import pytest
from werkzeug.datastructures import FileStorage

from config import Config
from app import create_app
from app.services.almacenamiento_service import (
    guardar_documento_privado,
    resolver_ruta_privada,
    eliminar_documento_privado,
)
from app.services.validaciones_service import (
    parse_fecha_iso,
    entero_en_rango,
    validar_ruc_peru,
)


@pytest.fixture
def app_privada(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase2-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'PRIVATE_STORAGE_DIR', str(tmp_path / 'storage_privado'), raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    app = create_app()
    with app.app_context():
        yield app


def test_almacenamiento_privado_fuera_de_static(app_privada):
    raiz = os.path.abspath(app_privada.config['PRIVATE_STORAGE_DIR'])
    static_dir = os.path.abspath(app_privada.static_folder)
    assert os.path.commonpath((static_dir, raiz)) != static_dir


def test_guardar_y_eliminar_pdf_valido(app_privada):
    contenido = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n'
    fs = FileStorage(stream=io.BytesIO(contenido), filename='Mi Certificado 2026.pdf')
    res = guardar_documento_privado(fs, subcarpeta='certificados')
    assert res.extension == 'pdf'
    assert res.mime_type == 'application/pdf'
    assert res.tamano_bytes == len(contenido)
    assert len(res.sha256) == 64

    ruta_abs = resolver_ruta_privada(res.ruta_relativa)
    assert ruta_abs is not None and os.path.isfile(ruta_abs)
    assert eliminar_documento_privado(res.ruta_relativa) is True
    assert not os.path.exists(ruta_abs)


def test_rechaza_pdf_falso_y_doble_extension(app_privada):
    falso = FileStorage(stream=io.BytesIO(b'<script>alert(1)</script>'), filename='cv.pdf')
    with pytest.raises(ValueError):
        guardar_documento_privado(falso, subcarpeta='cv')

    doble = FileStorage(stream=io.BytesIO(b'%PDF-1.4\n'), filename='doc.exe.pdf')
    with pytest.raises(ValueError):
        guardar_documento_privado(doble, subcarpeta='cv')


def test_rechaza_path_traversal(app_privada):
    assert resolver_ruta_privada('../../config.py') is None
    assert resolver_ruta_privada('/etc/passwd') is None


def test_validaciones_centralizadas():
    assert parse_fecha_iso('2026-11-24') == date(2026, 11, 24)
    assert parse_fecha_iso('', obligatoria=False) is None
    with pytest.raises(ValueError):
        parse_fecha_iso('', obligatoria=True)
    with pytest.raises(ValueError):
        parse_fecha_iso('24/11/2026')

    assert entero_en_rango('2024', 1990, 2100) == 2024
    with pytest.raises(ValueError):
        entero_en_rango('1800', 1990, 2100)

    assert validar_ruc_peru('20516641571') is True
    assert validar_ruc_peru('12345') is False
