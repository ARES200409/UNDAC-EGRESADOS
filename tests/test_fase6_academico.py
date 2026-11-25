"""Pruebas unitarias de la Fase 6: gestión académica y registro administrativo de egresados."""

import pytest
from config import Config
from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    Roles, Personal, Usuarios, UsuarioRoles,
    Facultades, ProgramasEstudio, Curriculas, Egresados, Auditoria
)


@pytest.fixture
def cliente_admin_acad(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase6-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        r_admin = Roles(nombre='administrador', descripcion='Admin')
        r_egr = Roles(nombre='egresado', descripcion='Egresado')
        fac = Facultades(nombre='Facultad de Ingeniería', codigo='FI', estado='activo')
        db.session.add_all([r_admin, r_egr, fac])
        db.session.flush()

        prog = ProgramasEstudio(
            id_facultad=fac.id_facultad,
            nombre='Ingeniería de Sistemas y Computación',
            codigo='17A4SI',
            estado='activo'
        )
        db.session.add(prog)
        db.session.flush()

        curr = Curriculas(id_programa=prog.id_programa, nombre='17A4SI', anio_inicio=2017, estado='activo')
        pers = Personal(nombres='Admin', apellido_paterno='Prueba', estado='activo')
        db.session.add_all([curr, pers])
        db.session.flush()

        u_admin = Usuarios(
            correo='admin.acad@undac.edu.pe',
            contrasena_hash=bcrypt.generate_password_hash('Admin2026!').decode('utf-8'),
            id_personal=pers.id_personal,
            estado='activo'
        )
        db.session.add(u_admin)
        db.session.flush()
        db.session.add(UsuarioRoles(id_usuario=u_admin.id_usuario, id_rol=r_admin.id_rol))
        db.session.commit()

        with app.test_client() as client:
            client.post('/login', data={
                'correo': 'admin.acad@undac.edu.pe',
                'contrasena': 'Admin2026!',
                'rol': str(r_admin.id_rol),
            })
            yield client, app, curr.id_curricula


def test_admin_registra_egresado_y_cuenta(cliente_admin_acad):
    client, app, id_curricula = cliente_admin_acad

    r = client.post('/admin/egresados/nuevo', data={
        'dni': '71234567',
        'codigo_universitario': '2020100001',
        'apellido_paterno': 'ROJAS',
        'apellido_materno': 'MENDOZA',
        'nombres': 'Lucia Fernanda',
        'genero': 'F',
        'id_curricula': str(id_curricula),
        'anio_ingreso': '2020',
        'anio_egreso': '2025',
        'periodo': '2025-I',
        'correo_institucional': 'lucia.rojas@undac.edu.pe',
        'telefono': '999888777',
        'crear_cuenta': '1',
        'contrasena': 'Lucia2026!',
    }, follow_redirects=True)
    assert r.status_code == 200
    assert 'ROJAS' in r.get_data(as_text=True)

    with app.app_context():
        egr = Egresados.query.filter_by(dni='71234567').first()
        assert egr is not None
        assert egr.usuario is not None
        assert egr.usuario.correo == 'lucia.rojas@undac.edu.pe'
        assert Auditoria.query.filter_by(accion='crear_egresado_admin').count() == 1

    # Duplicado de DNI debe rechazarse limpiamente
    r_dup = client.post('/admin/egresados/nuevo', data={
        'dni': '71234567',
        'apellido_paterno': 'OTRO',
        'nombres': 'Otro',
        'id_curricula': str(id_curricula),
    }, follow_redirects=True)
    assert 'Ya existe un egresado registrado con ese DNI' in r_dup.get_data(as_text=True)


def test_filtro_anio_invalido_en_egresados_no_falla(cliente_admin_acad):
    client, _, _ = cliente_admin_acad
    r = client.get('/admin/egresados?anio_egreso=abc')
    assert r.status_code == 200
