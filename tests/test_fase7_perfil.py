"""Pruebas unitarias de la Fase 7: completitud del perfil, privacidad y validación de empleos."""

import pytest
from config import Config
from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    Roles, Facultades, ProgramasEstudio, Curriculas,
    Egresados, Usuarios, UsuarioRoles, Sectores, Empresas, Auditoria
)
from app.services.perfil_service import calcular_completitud_perfil


@pytest.fixture
def cliente_egresado_perfil(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase7-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        rol_egr = Roles(nombre='egresado', descripcion='Egresado')
        fac = Facultades(nombre='Facultad de Ingeniería', codigo='FI', estado='activo')
        sec = Sectores(nombre='Tecnología')
        db.session.add_all([rol_egr, fac, sec])
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
        emp = Empresas(ruc='20600171221', razon_social='Empresa Demo SAC', id_sector=sec.id_sector, estado='activa')
        db.session.add_all([curr, emp])
        db.session.flush()

        egr = Egresados(
            dni='72223334',
            codigo_universitario='2020222333',
            apellido_paterno='PEREZ',
            nombres='Juan Carlos',
            correo_institucional='juan.perez@undac.edu.pe',
            id_curricula=curr.id_curricula,
        )
        db.session.add(egr)
        db.session.flush()

        u = Usuarios(
            correo='juan.perez@undac.edu.pe',
            contrasena_hash=bcrypt.generate_password_hash('Clave2026!').decode('utf-8'),
            id_egresado=egr.id_egresado,
            estado='activo'
        )
        db.session.add(u)
        db.session.flush()
        db.session.add(UsuarioRoles(id_usuario=u.id_usuario, id_rol=rol_egr.id_rol))
        db.session.commit()

        with app.test_client() as client:
            client.post('/login', data={
                'correo': 'juan.perez@undac.edu.pe',
                'contrasena': 'Clave2026!',
                'rol': str(rol_egr.id_rol),
            })
            yield client, app, egr.id_egresado, emp.id_empresa


def test_editar_perfil_completitud_y_privacidad(cliente_egresado_perfil):
    client, app, id_egr, _ = cliente_egresado_perfil

    with app.app_context():
        e_inicial = db.session.get(Egresados, id_egr)
        comp_inicial = calcular_completitud_perfil(e_inicial)
        assert comp_inicial['porcentaje'] == 0

    r = client.post('/perfil/editar', data={
        'telefono': '987654321',
        'distrito': 'Yanacancha',
        'titulo_cv': 'Ingeniero de Sistemas',
        'perfil_profesional': 'Especialista en Python y datos.',
        'situacion_laboral': 'empleado',
        'control_privacidad_presente': '1',
        'perfil_publico': '1',
    }, follow_redirects=True)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert '50% (4/8)' in html
    assert 'Compartido con empresas validadas' in html

    with app.app_context():
        assert Auditoria.query.filter_by(accion='editar_perfil').count() == 1


def test_nuevo_empleo_rechaza_fechas_invalidas_sin_error_500(cliente_egresado_perfil):
    client, _, _, id_empresa = cliente_egresado_perfil

    r = client.post('/empleos/nuevo', data={
        'id_empresa': str(id_empresa),
        'cargo': 'Analista TI',
        'fecha_inicio': 'no-es-fecha',
    }, follow_redirects=True)
    assert r.status_code == 200
    assert 'Formato de fecha inválido' in r.get_data(as_text=True)
