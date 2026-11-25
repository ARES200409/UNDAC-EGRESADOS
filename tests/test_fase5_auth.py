"""Pruebas unitarias de la Fase 5: bloqueo por intentos fallidos, rol empresa y auditoría."""

import pytest
from config import Config
from app import create_app
from app.extensions import db, bcrypt
from app.models import Roles, Usuarios, UsuarioRoles, Sectores, Empresas, Auditoria


@pytest.fixture
def cliente_auth(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase5-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)
    monkeypatch.setattr(Config, 'LOGIN_MAX_ATTEMPTS', 3, raising=False)
    monkeypatch.setattr(Config, 'LOGIN_LOCKOUT_SECONDS', 120, raising=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        rol_admin = Roles(nombre='administrador', descripcion='Admin')
        rol_emp = Roles(nombre='empresa', descripcion='Empresa')
        sector = Sectores(nombre='Tecnología')
        db.session.add_all([rol_admin, rol_emp, sector])
        db.session.flush()

        usuario = Usuarios(
            correo='admin.test@undac.edu.pe',
            contrasena_hash=bcrypt.generate_password_hash('ClaveSegura2026').decode('utf-8'),
            estado='activo',
        )
        db.session.add(usuario)
        db.session.flush()
        db.session.add(UsuarioRoles(id_usuario=usuario.id_usuario, id_rol=rol_admin.id_rol))
        db.session.commit()

        with app.test_client() as client:
            yield client, app, rol_admin.id_rol, rol_emp.id_rol, sector.id_sector


def test_bloqueo_por_intentos_fallidos_y_auditoria(cliente_auth):
    client, app, id_rol_admin, _, _ = cliente_auth

    for _ in range(3):
        r = client.post('/login', data={
            'correo': 'admin.test@undac.edu.pe',
            'contrasena': 'incorrecta',
            'rol': str(id_rol_admin),
        }, follow_redirects=True)
        assert r.status_code == 200

    with app.app_context():
        u = Usuarios.query.filter_by(correo='admin.test@undac.edu.pe').first()
        assert u.bloqueado_hasta is not None
        eventos = Auditoria.query.filter_by(modulo='auth').all()
        assert any(e.accion == 'login_bloqueo_activado' for e in eventos)

    # Incluso con clave correcta debe seguir bloqueado temporalmente
    r_bloq = client.post('/login', data={
        'correo': 'admin.test@undac.edu.pe',
        'contrasena': 'ClaveSegura2026',
        'rol': str(id_rol_admin),
    }, follow_redirects=True)
    assert 'bloqueada temporalmente' in r_bloq.get_data(as_text=True).lower()


def test_registro_empresa_pendiente_y_activacion(cliente_auth):
    client, app, _, id_rol_emp, id_sector = cliente_auth

    r_reg = client.post('/registro-empresa', data={
        'ruc': '20516641599',
        'razon_social': 'Tech Pasco SAC',
        'nombre_comercial': 'Tech Pasco',
        'id_sector': str(id_sector),
        'correo': 'rrhh@techpasco.pe',
        'contrasena': 'Empresa2026!',
        'confirmar': 'Empresa2026!',
    }, follow_redirects=True)
    assert r_reg.status_code == 200
    assert 'validará tu empresa' in r_reg.get_data(as_text=True)

    # Mientras esté pendiente no debe poder iniciar sesión
    r_pend = client.post('/login', data={
        'correo': 'rrhh@techpasco.pe',
        'contrasena': 'Empresa2026!',
        'rol': str(id_rol_emp),
    }, follow_redirects=True)
    assert 'pendiente de validación' in r_pend.get_data(as_text=True).lower()

    # Al aprobar la empresa, el login debe funcionar
    with app.app_context():
        emp = Empresas.query.filter_by(ruc='20516641599').first()
        emp.estado = 'activa'
        db.session.commit()

    r_ok = client.post('/login', data={
        'correo': 'rrhh@techpasco.pe',
        'contrasena': 'Empresa2026!',
        'rol': str(id_rol_emp),
    }, follow_redirects=True)
    assert r_ok.status_code == 200
    assert 'Portal de empleadores' in r_ok.get_data(as_text=True) or 'Mi cuenta' in r_ok.get_data(as_text=True)
