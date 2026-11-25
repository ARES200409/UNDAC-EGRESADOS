"""Pruebas de seguridad e integridad de Fase 8: gestión documental privada."""

import io
import os
import pytest
from config import Config
from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    Roles, Facultades, ProgramasEstudio, Curriculas,
    Egresados, Personal, Usuarios, UsuarioRoles,
    Sectores, Empresas, DocumentosEgresado, AutorizacionesDocumentales,
    Notificaciones, Auditoria
)


@pytest.fixture
def entorno_docs(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase8-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'PRIVATE_STORAGE_DIR', str(tmp_path / 'storage_privado'), raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        r_admin = Roles(nombre='administrador', descripcion='Admin')
        r_egr = Roles(nombre='egresado', descripcion='Egresado')
        r_emp = Roles(nombre='empresa', descripcion='Empresa')
        fac = Facultades(nombre='Facultad de Ingeniería', codigo='FI', estado='activo')
        sec = Sectores(nombre='Software')
        db.session.add_all([r_admin, r_egr, r_emp, fac, sec])
        db.session.flush()

        prog = ProgramasEstudio(id_facultad=fac.id_facultad, nombre='Ingeniería de Sistemas y Computación', codigo='17A4SI', estado='activo')
        db.session.add(prog)
        db.session.flush()
        curr = Curriculas(id_programa=prog.id_programa, nombre='17A4SI', anio_inicio=2017, estado='activo')
        db.session.add(curr)
        db.session.flush()

        # Egresado 1 (dueño) y Egresado 2 (otro usuario)
        e1 = Egresados(dni='70000011', apellido_paterno='UNO', nombres='Egresado', id_curricula=curr.id_curricula)
        e2 = Egresados(dni='70000022', apellido_paterno='DOS', nombres='Otro', id_curricula=curr.id_curricula)
        pers = Personal(nombres='Admin', apellido_paterno='Doc', estado='activo')
        emp = Empresas(ruc='20600171221', razon_social='Empresa Test', id_sector=sec.id_sector, estado='activa')
        db.session.add_all([e1, e2, pers, emp])
        db.session.flush()

        pw = bcrypt.generate_password_hash('Clave2026!').decode('utf-8')
        u1 = Usuarios(correo='egr1@undac.edu.pe', contrasena_hash=pw, id_egresado=e1.id_egresado, estado='activo')
        u2 = Usuarios(correo='egr2@undac.edu.pe', contrasena_hash=pw, id_egresado=e2.id_egresado, estado='activo')
        u_adm = Usuarios(correo='adm@undac.edu.pe', contrasena_hash=pw, id_personal=pers.id_personal, estado='activo')
        u_emp = Usuarios(correo='emp@empresa.pe', contrasena_hash=pw, id_empresa=emp.id_empresa, estado='activo')
        db.session.add_all([u1, u2, u_adm, u_emp])
        db.session.flush()

        db.session.add_all([
            UsuarioRoles(id_usuario=u1.id_usuario, id_rol=r_egr.id_rol),
            UsuarioRoles(id_usuario=u2.id_usuario, id_rol=r_egr.id_rol),
            UsuarioRoles(id_usuario=u_adm.id_usuario, id_rol=r_admin.id_rol),
            UsuarioRoles(id_usuario=u_emp.id_usuario, id_rol=r_emp.id_rol),
        ])
        db.session.commit()

        ids = {
            'r_egr': r_egr.id_rol, 'r_adm': r_admin.id_rol, 'r_emp': r_emp.id_rol,
            'e1': e1.id_egresado, 'emp': emp.id_empresa,
        }

    yield app, ids


def test_flujo_documental_privado_y_aislamiento_entre_usuarios(entorno_docs):
    app, ids = entorno_docs

    # 1. Egresado 1 sube un PDF real
    c1 = app.test_client()
    c1.post('/login', data={'correo': 'egr1@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_egr'])})
    pdf_bytes = b'%PDF-1.4\n%TestDoc\n'
    r_subir = c1.post('/documentos/subir', data={
        'nombre': 'CV Profesional',
        'categoria': 'cv',
        'es_cv_principal': '1',
        'archivo': (io.BytesIO(pdf_bytes), 'cv_2026.pdf'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert r_subir.status_code == 200
    assert 'CV Profesional' in r_subir.get_data(as_text=True)

    with app.app_context():
        doc = DocumentosEgresado.query.first()
        assert doc is not None and doc.es_cv_principal == 1
        id_doc = doc.id_documento

    # 2. Dueño puede descargar
    r_ok = c1.get(f'/documentos/{id_doc}/archivo')
    assert r_ok.status_code == 200
    assert r_ok.data == pdf_bytes
    r_ok.close()

    # 3. Egresado 2 NO puede descargar, reemplazar ni eliminar (403)
    c2 = app.test_client()
    c2.post('/login', data={'correo': 'egr2@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_egr'])})
    assert c2.get(f'/documentos/{id_doc}/archivo').status_code == 403
    assert c2.post(f'/documentos/{id_doc}/eliminar').status_code == 403

    # 4. Empresa sin autorización NO puede descargar (403)
    c_emp = app.test_client()
    c_emp.post('/login', data={'correo': 'emp@empresa.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_emp'])})
    assert c_emp.get(f'/documentos/{id_doc}/archivo').status_code == 403

    # 5. Con autorización expresa, la empresa SÍ puede descargar
    with app.app_context():
        db.session.add(AutorizacionesDocumentales(
            id_documento=id_doc, id_egresado=ids['e1'], id_empresa=ids['emp'], autorizado=1
        ))
        db.session.commit()
    r_emp_ok = c_emp.get(f'/documentos/{id_doc}/archivo')
    assert r_emp_ok.status_code == 200
    r_emp_ok.close()

    # 6. Admin observa documento con motivo y genera notificación al egresado
    c_adm = app.test_client()
    c_adm.post('/login', data={'correo': 'adm@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_adm'])})
    r_obs = c_adm.post(f'/admin/documentos/{id_doc}/revisar', data={
        'estado_validacion': 'observado',
        'observaciones': 'Falta firma en la última página',
    }, follow_redirects=True)
    assert r_obs.status_code == 200

    with app.app_context():
        doc_act = db.session.get(DocumentosEgresado, id_doc)
        assert doc_act.estado_validacion == 'observado'
        assert Notificaciones.query.count() == 1
        assert Auditoria.query.filter_by(accion='descarga_documento_denegada').count() >= 2
