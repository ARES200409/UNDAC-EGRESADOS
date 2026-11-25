"""Pruebas unitarias de Fase 9: campañas de seguimiento laboral y campos de empleo."""

import pytest
from config import Config
from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    Roles, Personal, Usuarios, UsuarioRoles,
    Facultades, ProgramasEstudio, Curriculas, CampanasSeguimiento, Auditoria
)


@pytest.fixture
def cliente_campanas(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase9-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        r_admin = Roles(nombre='administrador', descripcion='Admin')
        fac = Facultades(nombre='Facultad de Ingeniería', codigo='FI', estado='activo')
        pers = Personal(nombres='Admin', apellido_paterno='Seguimiento', estado='activo')
        db.session.add_all([r_admin, fac, pers])
        db.session.flush()

        prog = ProgramasEstudio(id_facultad=fac.id_facultad, nombre='Ingeniería de Sistemas y Computación', codigo='17A4SI', estado='activo')
        db.session.add(prog)
        db.session.flush()

        u = Usuarios(
            correo='admin.seg@undac.edu.pe',
            contrasena_hash=bcrypt.generate_password_hash('Clave2026!').decode('utf-8'),
            id_personal=pers.id_personal,
            estado='activo'
        )
        db.session.add(u)
        db.session.flush()
        db.session.add(UsuarioRoles(id_usuario=u.id_usuario, id_rol=r_admin.id_rol))
        db.session.commit()
        ids = {'rol': r_admin.id_rol, 'fac': fac.id_facultad, 'prog': prog.id_programa}

    client = app.test_client()
    client.post('/login', data={'correo': 'admin.seg@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['rol'])})
    yield client, app, ids


def test_crear_y_cerrar_campana_seguimiento(cliente_campanas):
    client, app, ids = cliente_campanas

    r = client.post('/admin/campanas/nueva', data={
        'nombre': 'Seguimiento Cohorte 2025 (1 año)',
        'descripcion': 'Medición de inserción laboral',
        'periodo_tipo': '1_anio',
        'id_facultad': str(ids['fac']),
        'id_programa': str(ids['prog']),
        'fecha_inicio': '2026-11-01',
        'fecha_fin': '2026-12-31',
        'activar': '1',
    }, follow_redirects=True)
    assert r.status_code == 200
    assert 'Seguimiento Cohorte 2025' in r.get_data(as_text=True)

    with app.app_context():
        camp = CampanasSeguimiento.query.first()
        assert camp is not None and camp.estado == 'activa'
        id_c = camp.id_campana

    r_close = client.post(f'/admin/campanas/{id_c}/estado', data={'estado': 'cerrada'}, follow_redirects=True)
    assert r_close.status_code == 200
    with app.app_context():
        assert db.session.get(CampanasSeguimiento, id_c).estado == 'cerrada'
        assert Auditoria.query.filter_by(accion='crear_campana').count() == 1


def test_campana_rechaza_fechas_invertidas(cliente_campanas):
    client, app, _ = cliente_campanas
    r = client.post('/admin/campanas/nueva', data={
        'nombre': 'Campaña Inválida',
        'periodo_tipo': '6_meses',
        'fecha_inicio': '2026-12-31',
        'fecha_fin': '2026-01-01',
    }, follow_redirects=True)
    assert 'La fecha de cierre no puede ser anterior al inicio' in r.get_data(as_text=True)
    with app.app_context():
        assert CampanasSeguimiento.query.count() == 0
