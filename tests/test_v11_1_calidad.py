"""Regresión V11.1. No conectarse a MySQL real ni modificar datos."""
from types import SimpleNamespace
from pathlib import Path
from app.admin.egresados import _celda_excel_segura
from app.utils.cv_pdf import _procesar_idiomas, generar_cv, _foto_circular


def test_export_excel_bloquea_formulas():
    for valor in ('=SUM(A1:A2)', '+CMD', '-123', '@HYPERLINK', '   =HYPERLINK("x","y")', '\t=SUM(A1)'):
        assert _celda_excel_segura(valor).startswith("'")
    assert _celda_excel_segura('Facultad de Ingeniería') == 'Facultad de Ingeniería'
    assert _celda_excel_segura(2026) == 2026


def test_idiomas_no_inventados():
    assert _procesar_idiomas([]) == []
    idiomas = [SimpleNamespace(nombre='Inglés', nivel_idioma='basico'),
               SimpleNamespace(nombre='Inglés', nivel_idioma='avanzado')]
    assert _procesar_idiomas(idiomas) == [('Inglés', 'Avanzado')]


def test_cv_con_datos_minimos_y_simbolos_xml():
    perfil = SimpleNamespace(nombres='Ana & María', apellido_paterno='Prueba',
        apellido_materno='<Demo>', titulo_cv='Egresada & aprendiendo', nivel_maximo='egresado',
        foto=None, telefono=None, correo_personal='correo@example.test',
        correo_institucional=None, distrito=None, provincia=None, perfil_profesional=None,
        linkedin=None, facebook=None, tiktok=None)
    pdf = generar_cv(perfil, [], [], [], [], [], [])
    assert pdf.getvalue()[:5] == b'%PDF-'
    assert len(pdf.getvalue()) > 1500


def test_cv_extenso_no_falla_por_tabla_de_una_fila():
    perfil = SimpleNamespace(nombres='Ana', apellido_paterno='Prueba',
        apellido_materno='', titulo_cv=None, nivel_maximo='egresado', foto=None,
        telefono=None, correo_personal=None, correo_institucional='x@test.local',
        distrito=None, provincia=None, perfil_profesional='Experiencia declarada',
        linkedin=None, facebook=None, tiktok=None)
    empleo = SimpleNamespace(cargo='Analista', empresa=None, fecha_inicio=None,
        fecha_fin=None, es_actual=False, funciones='Informes y datos\n'*5)
    pdf = generar_cv(perfil, [empleo]*20, [], [])
    assert pdf.getvalue()[:5] == b'%PDF-'
    assert len(pdf.getvalue()) > 2500


def test_foto_no_permita_salir_del_directorio_estatico():
    assert _foto_circular('../../config.py') is None


def test_carpeta_de_assets_es_local():
    base = Path(__file__).resolve().parents[1]
    for asset in ('app/static/css/v11_1_entrega.css',
                  'app/static/js/v11_indicadores.js',
                  'app/static/img/logo_undac_original.png',
                  'app/static/img/logo_sistemas_original.png'):
        assert (base / asset).is_file(), asset
