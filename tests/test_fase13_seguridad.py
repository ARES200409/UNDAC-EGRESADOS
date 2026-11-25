"""Pruebas de Fase 13: visor de auditoría y verificación integral de seguridad."""

import io
import pytest
from config import Config
from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    Roles, Personal, Egresados, Empresas, Sectores, Usuarios, UsuarioRoles,
    Facultades, ProgramasEstudio, Curriculas, DocumentosEgresado, Auditoria,
)


@pytest.fixture
def entorno_seguridad(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase13-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)
    monkeypatch.setattr(Config, 'PRIVATE_STORAGE_DIR', str(tmp_path / 'priv'), raising=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        r_admin = Roles(nombre='administrador', descripcion='Admin')
        r_egr = Roles(nombre='egresado', descripcion='Egresado')
        r_emp = Roles(nombre='empresa', descripcion='Empresa')
        fac = Facultades(nombre='Facultad de Ingeniería', codigo='FI', estado='activo')
        sec = Sectores(nombre='Tecnología')
        pers = Personal(nombres='Admin', apellido_paterno='Sec', estado='activo')
        db.session.add_all([r_admin, r_egr, r_emp, fac, sec, pers])
        db.session.flush()

        prog = ProgramasEstudio(id_facultad=fac.id_facultad, nombre='Ingeniería de Sistemas y Computación', codigo='17A4SI', estado='activo')
        db.session.add(prog)
        db.session.flush()
        curr = Curriculas(id_programa=prog.id_programa, nombre='17A4SI')
        db.session.add(curr)
        db.session.flush()

        e1 = Egresados(dni='72000001', nombres='Uno', apellido_paterno='Sec', id_curricula=curr.id_curricula)
        e2 = Egresados(dni='72000002', nombres='Dos', apellido_paterno='Sec', id_curricula=curr.id_curricula)
        emp = Empresas(ruc='20600999881', razon_social='Empresa Sec SAC', id_sector=sec.id_sector, estado='activa')
        db.session.add_all([e1, e2, emp])
        db.session.flush()

        pw = bcrypt.generate_password_hash('Clave2026!').decode('utf-8')
        u_adm = Usuarios(correo='adm.sec@undac.edu.pe', contrasena_hash=pw, id_personal=pers.id_personal, estado='activo')
        u_e1 = Usuarios(correo='e1.sec@undac.edu.pe', contrasena_hash=pw, id_egresado=e1.id_egresado, estado='activo')
        u_e2 = Usuarios(correo='e2.sec@undac.edu.pe', contrasena_hash=pw, id_egresado=e2.id_egresado, estado='activo')
        u_emp = Usuarios(correo='emp.sec@empresa.pe', contrasena_hash=pw, id_empresa=emp.id_empresa, estado='activo')
        db.session.add_all([u_adm, u_e1, u_e2, u_emp])
        db.session.flush()

        db.session.add_all([
            UsuarioRoles(id_usuario=u_adm.id_usuario, id_rol=r_admin.id_rol),
            UsuarioRoles(id_usuario=u_e1.id_usuario, id_rol=r_egr.id_rol),
            UsuarioRoles(id_usuario=u_e2.id_usuario, id_rol=r_egr.id_rol),
            UsuarioRoles(id_usuario=u_emp.id_usuario, id_rol=r_emp.id_rol),
        ])
        db.session.commit()
        ids = {'r_adm': r_admin.id_rol, 'r_egr': r_egr.id_rol, 'r_emp': r_emp.id_rol}

    yield app, ids


def test_visor_auditoria_y_aislamiento_seguridad(entorno_seguridad):
    app, ids = entorno_seguridad
    c_adm = app.test_client()
    c_e1 = app.test_client()
    c_e2 = app.test_client()
    c_emp = app.test_client()

    c_adm.post('/login', data={'correo': 'adm.sec@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_adm'])})
    c_e1.post('/login', data={'correo': 'e1.sec@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_egr'])})
    c_e2.post('/login', data={'correo': 'e2.sec@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_egr'])})
    c_emp.post('/login', data={'correo': 'emp.sec@empresa.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_emp'])})

    # 1. Egresado 1 sube documento privado
    r_up = c_e1.post('/documentos/subir', data={
        'nombre': 'Diploma Privado',
        'categoria': 'diploma',
        'archivo': (io.BytesIO(b'%PDF-1.4\n%Privado\n'), 'diploma.pdf'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert r_up.status_code == 200

    with app.app_context():
        doc = DocumentosEgresado.query.first()
        assert doc is not None
        id_doc = doc.id_documento
        ruta_int = doc.ruta_almacenamiento

    # 2. Documento privado NO debe ser accesible por /static/uploads/
    assert c_e2.get(f'/static/uploads/{ruta_int}').status_code == 404

    # 3. Egresado 2 y Empresa sin autorización reciben 403 al descargar documento ajeno
    assert c_e2.get(f'/documentos/{id_doc}/archivo').status_code == 403
    assert c_emp.get(f'/documentos/{id_doc}/archivo').status_code == 403

    # 4. Visor de auditoría restringido a admin/utsag
    r_e1_aud = c_e1.get('/admin/auditoria')
    r_emp_aud = c_emp.get('/admin/auditoria')
    assert r_e1_aud.status_code in (302, 403)
    assert r_emp_aud.status_code in (302, 403)
    assert 'Registro de Auditoría' not in r_e1_aud.get_data(as_text=True)
    assert 'Registro de Auditoría' not in r_emp_aud.get_data(as_text=True)

    r_aud = c_adm.get('/admin/auditoria?modulo=documentos&resultado=denegado')
    assert r_aud.status_code == 200
    assert 'Registro de Auditoría' in r_aud.get_data(as_text=True)
    with app.app_context():
        assert Auditoria.query.filter_by(modulo='documentos', resultado='denegado').count() >= 2
