"""Pruebas unitarias de Fase 12: reportes consolidados, filtros y exportación Excel/PDF."""

from datetime import date
import pytest
from config import Config
from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    Roles, Personal, Usuarios, UsuarioRoles, AsignacionesPersonal,
    Facultades, ProgramasEstudio, Curriculas, Egresados,
    DocumentosEgresado, Capacitaciones, CampanasSeguimiento,
)


@pytest.fixture
def entorno_reportes(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase12-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        r_admin = Roles(nombre='administrador', descripcion='Admin')
        r_coord = Roles(nombre='coordinador', descripcion='Coord')
        f1 = Facultades(nombre='Facultad de Ingeniería', codigo='FI', estado='activo')
        f2 = Facultades(nombre='Facultad de Educación', codigo='FE', estado='activo')
        p_adm = Personal(nombres='Admin', apellido_paterno='Rep', estado='activo')
        p_crd = Personal(nombres='Coord', apellido_paterno='Ing', estado='activo')
        db.session.add_all([r_admin, r_coord, f1, f2, p_adm, p_crd])
        db.session.flush()

        pr1 = ProgramasEstudio(id_facultad=f1.id_facultad, nombre='Ingeniería de Sistemas y Computación', codigo='17A4SI', estado='activo')
        pr2 = ProgramasEstudio(id_facultad=f2.id_facultad, nombre='Educación Primaria', codigo='EDU01', estado='activo')
        db.session.add_all([pr1, pr2])
        db.session.flush()

        cur1 = Curriculas(id_programa=pr1.id_programa, nombre='17A4SI')
        db.session.add(cur1)
        db.session.flush()

        e1 = Egresados(dni='71000001', nombres='Rosa', apellido_paterno='Vega', id_curricula=cur1.id_curricula, anio_egreso=2025)
        db.session.add(e1)
        db.session.flush()

        db.session.add(DocumentosEgresado(
            id_egresado=e1.id_egresado, nombre='CV 2026', categoria='cv',
            nombre_original='cv.pdf', nombre_interno='cv.pdf', ruta_almacenamiento='1/cv.pdf',
            extension='pdf', mime_type='application/pdf', tamano_bytes=1024, sha256='0' * 64,
            estado_validacion='validado',
        ))
        db.session.add(Capacitaciones(
            titulo='Seminario Python', tipo='seminario', fecha_inicio=date(2026, 11, 10),
            modalidad='virtual', estado='publicada',
        ))
        db.session.add(CampanasSeguimiento(
            nombre='Cohorte 2025', periodo_tipo='1_anio', estado='activa',
        ))

        pw = bcrypt.generate_password_hash('Clave2026!').decode('utf-8')
        u_adm = Usuarios(correo='adm.rep@undac.edu.pe', contrasena_hash=pw, id_personal=p_adm.id_personal, estado='activo')
        u_crd = Usuarios(correo='crd.rep@undac.edu.pe', contrasena_hash=pw, id_personal=p_crd.id_personal, estado='activo')
        db.session.add_all([u_adm, u_crd])
        db.session.flush()

        db.session.add_all([
            UsuarioRoles(id_usuario=u_adm.id_usuario, id_rol=r_admin.id_rol),
            UsuarioRoles(id_usuario=u_crd.id_usuario, id_rol=r_coord.id_rol),
            AsignacionesPersonal(
                id_personal=p_crd.id_personal, id_rol=r_coord.id_rol,
                id_facultad=f1.id_facultad, fecha_inicio=date(2026, 1, 1), estado='activo'
            ),
        ])
        db.session.commit()
        ids = {'r_adm': r_admin.id_rol, 'r_crd': r_coord.id_rol, 'f1': f1.id_facultad, 'f2': f2.id_facultad}

    yield app, ids


def test_reportes_consolidados_excel_pdf_y_ambito(entorno_reportes):
    app, ids = entorno_reportes
    c_adm = app.test_client()
    c_crd = app.test_client()

    c_adm.post('/login', data={'correo': 'adm.rep@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_adm'])})
    c_crd.post('/login', data={'correo': 'crd.rep@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_crd'])})

    # Vista HTML filtrada
    r_html = c_adm.get(f"/admin/reportes?id_facultad={ids['f1']}&fecha_desde=2026-01-01&fecha_hasta=2026-12-31")
    assert r_html.status_code == 200
    assert 'Reportes Consolidados' in r_html.get_data(as_text=True)

    # Excel consolidado
    r_xlsx = c_adm.get('/admin/reportes/excel')
    assert r_xlsx.status_code == 200
    assert r_xlsx.data.startswith(b'PK')
    r_xlsx.close()

    # PDF consolidado
    r_pdf = c_adm.get('/admin/reportes/pdf')
    assert r_pdf.status_code == 200
    assert r_pdf.data.startswith(b'%PDF')
    r_pdf.close()

    # Coordinador no puede consultar facultad ajena
    r_forb = c_crd.get(f"/admin/reportes?id_facultad={ids['f2']}")
    assert r_forb.status_code == 403
