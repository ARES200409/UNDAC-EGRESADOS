# tests/test_registro_dni.py
"""Tests del módulo de registro inteligente por DNI – NEXO UNDAC V9.

Cubre:
  - Validación de formato DNI en el endpoint
  - Control de acceso (acceso denegado sin sesión de registro)
  - Rate limiting
  - Respuesta de identity_service cuando UNDAC API responde / no responde
  - Sincronización académica: creación de historial
  - Aislamiento de historial entre egresados
  - Endpoints de historial (acceso propio vs ajeno)
"""

import pytest
from unittest.mock import patch, MagicMock

from app import create_app
from app.extensions import db as _db
from app.models import (
    Egresados, Usuarios, Roles, UsuarioRoles, Curriculas, ProgramasEstudio, Facultades,
    HistorialSyncAcademico,
)
from app.services import academic_sync_service


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    """Aplicación Flask configurada para tests."""
    test_app = create_app()
    test_app.config['TESTING'] = True
    test_app.config['WTF_CSRF_ENABLED'] = False
    test_app.config['SERVER_NAME'] = 'localhost'
    with test_app.app_context():
        yield test_app


@pytest.fixture(scope='session')
def _setup_db(app):
    """Crea datos mínimos para los tests de esta suite."""
    with app.app_context():
        # Facultad
        fac = Facultades.query.filter_by(nombre='Sistemas Test DNI').first()
        if not fac:
            fac = Facultades(nombre='Sistemas Test DNI', codigo='STDNI', estado='activo')
            _db.session.add(fac)
            _db.session.flush()

        # Programa
        prog = ProgramasEstudio.query.filter_by(codigo='STDNI01').first()
        if not prog:
            prog = ProgramasEstudio(id_facultad=fac.id_facultad, nombre='Ingeniería de Sistemas DNI Test',
                                     codigo='STDNI01', estado='activo')
            _db.session.add(prog)
            _db.session.flush()

        # Currícula
        cur = Curriculas.query.filter_by(nombre='20TDNI').first()
        if not cur:
            cur = Curriculas(id_programa=prog.id_programa, nombre='20TDNI',
                              anio_inicio=2020, estado='activo')
            _db.session.add(cur)
            _db.session.flush()

        # Rol egresado
        rol = Roles.query.filter_by(nombre='egresado').first()
        if not rol:
            rol = Roles(nombre='egresado', descripcion='Egresado test')
            _db.session.add(rol)
            _db.session.flush()

        # Egresado de prueba
        eg = Egresados.query.filter_by(dni='12345690').first()
        if not eg:
            eg = Egresados(
                dni='12345690', nombres='Prueba DNI', apellido_paterno='Test',
                apellido_materno='Sync', id_curricula=cur.id_curricula,
                anio_ingreso=2020, es_bachiller=0, es_titulado=0,
                tiene_maestria=0, tiene_doctorado=0, nivel_maximo='egresado',
                codigo_universitario='210000090',
            )
            _db.session.add(eg)
            _db.session.flush()

        # Egresado B (para test de aislamiento)
        eg2 = Egresados.query.filter_by(dni='12345691').first()
        if not eg2:
            eg2 = Egresados(
                dni='12345691', nombres='Otro DNI', apellido_paterno='Otro',
                apellido_materno='Egresado', id_curricula=cur.id_curricula,
                anio_ingreso=2021, es_bachiller=0, es_titulado=0,
                tiene_maestria=0, tiene_doctorado=0, nivel_maximo='egresado',
                codigo_universitario='210000091',
            )
            _db.session.add(eg2)
            _db.session.flush()

        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        bcrypt.init_app(app)
        hash_pw = bcrypt.generate_password_hash('TestPass123!').decode('utf-8')

        # Usuario del egresado A
        usr = Usuarios.query.filter_by(correo='dni_test@nexo.test').first()
        if not usr:
            usr = Usuarios(correo='dni_test@nexo.test', contrasena_hash=hash_pw,
                           id_egresado=eg.id_egresado, estado='activo')
            _db.session.add(usr)
            _db.session.flush()
            ur = UsuarioRoles(id_usuario=usr.id_usuario, id_rol=rol.id_rol)
            _db.session.add(ur)

        # Usuario del egresado B
        usr2 = Usuarios.query.filter_by(correo='dni_test2@nexo.test').first()
        if not usr2:
            usr2 = Usuarios(correo='dni_test2@nexo.test', contrasena_hash=hash_pw,
                            id_egresado=eg2.id_egresado, estado='activo')
            _db.session.add(usr2)
            _db.session.flush()
            ur2 = UsuarioRoles(id_usuario=usr2.id_usuario, id_rol=rol.id_rol)
            _db.session.add(ur2)

        _db.session.commit()
        return {'eg': eg, 'eg2': eg2, 'usr': usr, 'usr2': usr2}


@pytest.fixture
def client(app, _setup_db):
    with app.test_client() as c:
        with app.app_context():
            yield c


# ─────────────────────────────────────────────────────────────────────
# Tests del endpoint GET /api/dni/<dni>
# ─────────────────────────────────────────────────────────────────────

class TestEndpointConsultaDni:

    def test_dni_menos_de_8_digitos_devuelve_400(self, client):
        with client.session_transaction() as sess:
            sess['consultando_dni'] = True
        resp = client.get('/api/dni/1234567')
        assert resp.status_code == 400
        assert b'invalido' in resp.data.lower() or resp.get_json().get('error') == 'dni_invalido'

    def test_dni_con_letras_devuelve_400(self, client):
        with client.session_transaction() as sess:
            sess['consultando_dni'] = True
        resp = client.get('/api/dni/1234567A')
        assert resp.status_code == 400

    def test_sin_sesion_de_registro_devuelve_403(self, client):
        # Limpiar sesión
        with client.session_transaction() as sess:
            sess.clear()
        resp = client.get('/api/dni/12345678')
        assert resp.status_code == 403

    def test_dni_8_digitos_con_sesion_activa_responde_json(self, client, app):
        with client.session_transaction() as sess:
            sess['consultando_dni'] = True

        with app.app_context():
            # Mockear identity_service para no hacer llamadas reales
            with patch('app.api_dni.routes.consultar_completo') as mock_cc:
                mock_cc.return_value = {
                    "dni": "12345678",
                    "encontrado": False,
                    "estado": "sin_datos",
                    "datos_personales": {},
                    "datos_academicos": {},
                    "grados_titulos": [],
                    "fuentes": {},
                    "timestamp": "2026-11-25T00:00:00Z",
                }
                resp = client.get('/api/dni/12345678')
                assert resp.status_code == 200
                datos = resp.get_json()
                assert 'encontrado' in datos
                assert datos['dni'] == '12345678'

    def test_rate_limit_activa_tras_limite(self, client, app):
        """Después de DNI_LOOKUP_RATE_LIMIT consultas el endpoint devuelve 429."""
        app.config['DNI_LOOKUP_RATE_LIMIT'] = 2
        # Limpiar store interno
        from app.api_dni import routes as r
        r._RATE_STORE.clear()

        with client.session_transaction() as sess:
            sess['consultando_dni'] = True

        with app.app_context():
            with patch('app.api_dni.routes.consultar_completo') as mock_cc:
                mock_cc.return_value = {"dni":"99999999","encontrado":False,"estado":"sin_datos",
                                         "datos_personales":{},"datos_academicos":{},
                                         "grados_titulos":[],"fuentes":{},"timestamp":"2026-11-25T00:00:00Z"}
                r1 = client.get('/api/dni/99999901')
                r2 = client.get('/api/dni/99999902')
                r3 = client.get('/api/dni/99999903')   # debe ser 429
                assert r1.status_code == 200
                assert r2.status_code == 200
                assert r3.status_code == 429

        app.config['DNI_LOOKUP_RATE_LIMIT'] = 10


# ─────────────────────────────────────────────────────────────────────
# Tests de identity_service
# ─────────────────────────────────────────────────────────────────────

class TestIdentityService:

    def test_dni_invalido_no_consulta_fuentes(self, app):
        from app.services.identity_service import consultar_completo
        with app.app_context():
            with patch('app.services.identity_service.buscar_por_dni') as mock_undac, \
                 patch('app.services.identity_service.consultar_reniec') as mock_reniec, \
                 patch('app.services.identity_service.consultar_sunedu') as mock_sunedu:

                result = consultar_completo('1234567')   # 7 dígitos
                assert result['estado'] == 'dni_invalido'
                mock_undac.assert_not_called()
                mock_reniec.assert_not_called()
                mock_sunedu.assert_not_called()

    def test_dni_8_digitos_llama_tres_fuentes(self, app):
        from app.services.identity_service import consultar_completo
        with app.app_context():
            resp_undac  = {"fuente":"undac_api","disponible":False,"datos":None,"motivo":"codigo_no_encontrado"}
            resp_reniec = {"fuente":"reniec","disponible":False,"datos":None,"motivo":"sin_credenciales"}
            resp_sunedu = {"fuente":"sunedu","disponible":False,"grados":[],"motivo":"sin_credenciales"}

            with patch('app.services.identity_service.buscar_por_dni', return_value=resp_undac) as mu, \
                 patch('app.services.identity_service.consultar_reniec', return_value=resp_reniec) as mr, \
                 patch('app.services.identity_service.consultar_sunedu', return_value=resp_sunedu) as ms:

                result = consultar_completo('12345678')
                mu.assert_called_once_with('12345678')
                mr.assert_called_once_with('12345678')
                ms.assert_called_once_with('12345678')
                assert result['estado'] == 'sin_datos'
                assert result['encontrado'] is False

    def test_datos_undac_consolidan_en_respuesta(self, app):
        from app.services.identity_service import consultar_completo
        with app.app_context():
            resp_undac = {
                "fuente": "undac_api", "disponible": True, "motivo": None,
                "datos": {
                    "nombres": "JUAN", "apellido_paterno": "PEREZ",
                    "apellido_materno": "LOPEZ", "fecha_nacimiento": "2000-01-15",
                    "genero": "M", "codigo_universitario": "210001234",
                    "curricula": "17A4SI", "programa_facultad": "Ingeniería de Sistemas",
                    "id_escuela": "", "anio_ingreso": "2017",
                    "domicilio": "", "correo_institucional": "",
                    "rol": "EG",
                }
            }
            resp_reniec = {"fuente":"reniec","disponible":False,"datos":None,"motivo":"sin_credenciales"}
            resp_sunedu = {"fuente":"sunedu","disponible":False,"grados":[],"motivo":"sin_credenciales"}

            with patch('app.services.identity_service.buscar_por_dni', return_value=resp_undac), \
                 patch('app.services.identity_service.consultar_reniec', return_value=resp_reniec), \
                 patch('app.services.identity_service.consultar_sunedu', return_value=resp_sunedu):

                result = consultar_completo('12345678')
                assert result['encontrado'] is True
                assert result['datos_personales']['nombres']['valor'] == 'JUAN'
                assert result['datos_personales']['nombres']['fuente'] == 'undac_api'
                assert result['datos_academicos']['curricula']['valor'] == '17A4SI'


# ─────────────────────────────────────────────────────────────────────
# Tests de sincronización y historial
# ─────────────────────────────────────────────────────────────────────

class TestSincronizacion:

    def test_sync_crea_entradas_en_historial(self, app, _setup_db):
        eg = _setup_db['eg']
        with app.app_context():
            # Recargar el egresado en esta sesión
            egresado = _db.session.get(Egresados, eg.id_egresado)
            id_eg = egresado.id_egresado

            # Limpiar historial previo de esta prueba
            HistorialSyncAcademico.query.filter_by(id_egresado=id_eg, fuente='sunedu').delete()
            _db.session.commit()

            resp_undac  = {"fuente":"undac_api","disponible":False,"datos":None,"motivo":"codigo_no_encontrado"}
            resp_reniec = {"fuente":"reniec","disponible":False,"datos":None,"motivo":"sin_credenciales"}
            resp_sunedu = {
                "fuente": "sunedu", "disponible": True, "motivo": None,
                "grados": [{"tipo":"BACHILLER","denominacion":"Bachiller en Ingeniería de Sistemas",
                             "universidad":"UNDAC","fecha":"2025-01-01",
                             "es_bachiller":True,"es_titulado":False,"es_maestria":False,"es_doctorado":False}]
            }

            with patch('app.services.identity_service.buscar_por_dni', return_value=resp_undac), \
                 patch('app.services.identity_service.consultar_reniec', return_value=resp_reniec), \
                 patch('app.services.identity_service.consultar_sunedu', return_value=resp_sunedu):

                from app.services.academic_sync_service import sincronizar_egresado
                resultado = sincronizar_egresado(id_eg, operador='sistema')

            assert resultado['ok'] is True
            # Debe haber creado al menos una entrada en historial (es_bachiller)
            entradas = HistorialSyncAcademico.query.filter_by(
                id_egresado=id_eg, fuente='sunedu', campo='es_bachiller'
            ).all()
            assert len(entradas) >= 1
            assert entradas[0].valor_nuevo == '1'

    def test_sync_no_crea_historial_si_no_hay_cambios(self, app, _setup_db):
        eg = _setup_db['eg']
        with app.app_context():
            egresado = _db.session.get(Egresados, eg.id_egresado)
            id_eg = egresado.id_egresado

            # Poner es_bachiller en 1 (ya actualizado)
            egresado.es_bachiller = 1
            _db.session.commit()

            prev_count = HistorialSyncAcademico.query.filter_by(id_egresado=id_eg).count()

            resp_undac  = {"fuente":"undac_api","disponible":False,"datos":None,"motivo":"codigo_no_encontrado"}
            resp_reniec = {"fuente":"reniec","disponible":False,"datos":None,"motivo":"sin_credenciales"}
            resp_sunedu = {
                "fuente": "sunedu", "disponible": True, "motivo": None,
                "grados": [{"es_bachiller":True,"es_titulado":False,"es_maestria":False,"es_doctorado":False}]
            }

            with patch('app.services.identity_service.buscar_por_dni', return_value=resp_undac), \
                 patch('app.services.identity_service.consultar_reniec', return_value=resp_reniec), \
                 patch('app.services.identity_service.consultar_sunedu', return_value=resp_sunedu):

                from app.services.academic_sync_service import sincronizar_egresado
                resultado = sincronizar_egresado(id_eg, operador='sistema')

            new_count = HistorialSyncAcademico.query.filter_by(id_egresado=id_eg).count()
            assert new_count == prev_count  # Sin cambio → sin nueva entrada

    def test_egresado_no_puede_ver_historial_de_otro(self, client, app, _setup_db):
        """El egresado A no puede ver el historial del egresado B."""
        usr = _setup_db['usr']
        eg2 = _setup_db['eg2']

        # Iniciar sesión como egresado A
        with app.app_context():
            resp = client.post('/login', data={
                'correo': 'dni_test@nexo.test',
                'contrasena': 'TestPass123!',
            }, follow_redirects=True)

        with app.app_context():
            resp_hist = client.get(f'/api/egresado/{eg2.id_egresado}/historial')
            # Debe ser 403 (acceso denegado) o 302 (redirect a login)
            assert resp_hist.status_code in (403, 302, 401)
