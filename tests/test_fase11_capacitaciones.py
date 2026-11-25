"""Pruebas unitarias de Fase 11: capacitaciones, cupos, constancias y notificaciones."""

import pytest
from config import Config
from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    Roles, Personal, Egresados, Usuarios, UsuarioRoles,
    Facultades, ProgramasEstudio, Curriculas,
    Capacitaciones, InscripcionesCapacitacion, Notificaciones,
)


@pytest.fixture
def entorno_cap(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', 'clave-test-fase11-no-usar-en-produccion', raising=False)
    monkeypatch.setattr(Config, 'TESTING', True, raising=False)
    monkeypatch.setattr(Config, 'WTF_CSRF_ENABLED', False, raising=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        r_admin = Roles(nombre='administrador', descripcion='Admin')
        r_egr = Roles(nombre='egresado', descripcion='Egresado')
        fac = Facultades(nombre='Facultad de Ingeniería', codigo='FI', estado='activo')
        pers = Personal(nombres='Coord', apellido_paterno='Cap', estado='activo')
        db.session.add_all([r_admin, r_egr, fac, pers])
        db.session.flush()

        prog = ProgramasEstudio(id_facultad=fac.id_facultad, nombre='Ingeniería de Sistemas y Computación', codigo='17A4SI', estado='activo')
        db.session.add(prog)
        db.session.flush()

        curr = Curriculas(id_programa=prog.id_programa, nombre='17A4SI')
        db.session.add(curr)
        db.session.flush()

        e1 = Egresados(
            dni='70000101', nombres='Ana', apellido_paterno='Rojas',
            id_curricula=curr.id_curricula, anio_egreso=2024
        )
        e2 = Egresados(
            dni='70000102', nombres='Luis', apellido_paterno='Diaz',
            id_curricula=curr.id_curricula, anio_egreso=2024
        )
        db.session.add_all([e1, e2])
        db.session.flush()

        clave = bcrypt.generate_password_hash('Clave2026!').decode('utf-8')
        u_adm = Usuarios(correo='adm.cap@undac.edu.pe', contrasena_hash=clave, id_personal=pers.id_personal, estado='activo')
        u_e1 = Usuarios(correo='ana.cap@undac.edu.pe', contrasena_hash=clave, id_egresado=e1.id_egresado, estado='activo')
        u_e2 = Usuarios(correo='luis.cap@undac.edu.pe', contrasena_hash=clave, id_egresado=e2.id_egresado, estado='activo')
        db.session.add_all([u_adm, u_e1, u_e2])
        db.session.flush()

        db.session.add_all([
            UsuarioRoles(id_usuario=u_adm.id_usuario, id_rol=r_admin.id_rol),
            UsuarioRoles(id_usuario=u_e1.id_usuario, id_rol=r_egr.id_rol),
            UsuarioRoles(id_usuario=u_e2.id_usuario, id_rol=r_egr.id_rol),
        ])
        db.session.commit()
        ids = {'r_adm': r_admin.id_rol, 'r_egr': r_egr.id_rol, 'u_e1': u_e1.id_usuario, 'u_e2': u_e2.id_usuario}

    yield app, ids


def test_flujo_capacitaciones_aforo_constancia_y_notificaciones(entorno_cap):
    app, ids = entorno_cap
    c_adm = app.test_client()
    c_e1 = app.test_client()
    c_e2 = app.test_client()

    c_adm.post('/login', data={'correo': 'adm.cap@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_adm'])})
    c_e1.post('/login', data={'correo': 'ana.cap@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_egr'])})
    c_e2.post('/login', data={'correo': 'luis.cap@undac.edu.pe', 'contrasena': 'Clave2026!', 'rol': str(ids['r_egr'])})

    # 1. Admin crea capacitación con aforo 1
    r_new = c_adm.post('/admin/capacitaciones/nueva', data={
        'titulo': 'Taller de Arquitectura Cloud',
        'tipo': 'taller',
        'modalidad': 'virtual',
        'fecha_inicio': '2026-12-01',
        'capacidad_maxima': '1',
        'estado': 'publicada',
    }, follow_redirects=True)
    assert r_new.status_code == 200
    assert 'Taller de Arquitectura Cloud' in r_new.get_data(as_text=True)

    with app.app_context():
        cap = Capacitaciones.query.first()
        assert cap is not None
        id_cap = cap.id_capacitacion

    # 2. Egresado 1 se inscribe y recibe notificación
    r_i1 = c_e1.post(f'/capacitaciones/{id_cap}/inscribirse', follow_redirects=True)
    assert r_i1.status_code == 200
    assert 'Inscripción confirmada' in r_i1.get_data(as_text=True)

    # 3. Egresado 2 intenta inscribirse pero aforo está lleno
    r_i2 = c_e2.post(f'/capacitaciones/{id_cap}/inscribirse', follow_redirects=True)
    assert r_i2.status_code == 200
    assert 'aforo máximo' in r_i2.get_data(as_text=True)

    with app.app_context():
        ins1 = InscripcionesCapacitacion.query.filter_by(id_capacitacion=id_cap).first()
        assert ins1 is not None and ins1.estado == 'inscrito'
        id_ins = ins1.id_inscripcion

    # 4. Admin marca asistencia y genera código de constancia
    r_as = c_adm.post(f'/admin/capacitaciones/inscripcion/{id_ins}/asistencia', data={'estado': 'asistio'}, follow_redirects=True)
    assert r_as.status_code == 200
    with app.app_context():
        ins_act = db.session.get(InscripcionesCapacitacion, id_ins)
        assert ins_act.estado == 'asistio'
        assert ins_act.codigo_constancia and ins_act.codigo_constancia.startswith('UNDAC-CAP')
        notifs_e1 = Notificaciones.query.filter_by(id_usuario=ids['u_e1']).all()
        assert len(notifs_e1) == 2
        id_n1 = notifs_e1[0].id_notificacion

    # 5. Aislamiento: Egresado 2 no puede marcar como leída notificación de Egresado 1
    c_e2.post(f'/notificaciones/{id_n1}/leer')
    with app.app_context():
        assert db.session.get(Notificaciones, id_n1).leida == 0

    # 6. Egresado 1 marca todas como leídas
    r_all = c_e1.post('/notificaciones/leer-todas', follow_redirects=True)
    assert r_all.status_code == 200
    with app.app_context():
        assert Notificaciones.query.filter_by(id_usuario=ids['u_e1'], leida=0).count() == 0
