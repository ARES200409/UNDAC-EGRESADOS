from flask import render_template, request, send_file, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, case
from datetime import date
from app.utils.v8_db import tablas_v8_disponibles
from app.admin import admin
from app.admin.helpers import requiere_rol, _alcance_programas, _facultades_de_coordinador
from app.admin.informes import generar_informe_pdf
from app.admin.paneles_v91 import construir_contexto_panel
from app.admin.analitica_sistemas import construir_analitica
from app.extensions import db
from app.models import Egresados, Curriculas, ProgramasEstudio, Facultades, Empresas, Usuarios, Empleos, Sectores, OfertasLaborales, Postulaciones

def obtener_metricas_dashboard(rol_activo, id_personal, id_facultad=None, id_programa=None):
    """
    Centraliza la lógica de consulta y agregación de datos para el dashboard y los PDF.
    Resuelve el alcance relacional en la base de datos sin saturar memoria.
    """
    # 1. Definir subconsulta de IDs según el alcance del usuario y filtros
    alcance = _alcance_programas(rol_activo, id_personal)
    
    # Para docente responsable, se forzan sus programas
    if rol_activo == 'docente_responsable':
        id_facultad, id_programa = None, None

    q_ids = db.session.query(Egresados.id_egresado).join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)

    if alcance is not None:
        if alcance:
            q_ids = q_ids.filter(Curriculas.id_programa.in_(alcance))
        else:
            q_ids = q_ids.filter(db.literal(False))

    if id_programa:
        q_ids = q_ids.filter(Curriculas.id_programa == id_programa)
    elif id_facultad:
        q_ids = q_ids.join(ProgramasEstudio, Curriculas.id_programa == ProgramasEstudio.id_programa)\
                     .filter(ProgramasEstudio.id_facultad == id_facultad)

    # Subconsulta SQL directa (sin cargar IDs en memoria Python)
    subq_egresados = q_ids.subquery()
    base_query = Egresados.query.filter(Egresados.id_egresado.in_(subq_egresados))

    # 2. Resumen General / KPIs (Consultas consolidadas)
    total_egresados = base_query.count()

    # 3. Empleabilidad y Busqueda Laboral
    total_con_cuenta = base_query.join(Usuarios, Usuarios.id_egresado == Egresados.id_egresado).distinct().count()
    con_empleo_actual = base_query.join(Empleos, Empleos.id_egresado == Egresados.id_egresado)\
                                  .filter(Empleos.es_actual == 1).distinct().count()
    tasa_empleabilidad = round((con_empleo_actual / total_con_cuenta * 100), 1) if total_con_cuenta else 0.0
    sin_empleo_reportado = max(0, total_con_cuenta - con_empleo_actual)
    bachilleres = base_query.filter(Egresados.es_bachiller == 1).count()
    titulados = base_query.filter(Egresados.es_titulado == 1).count()

    # 4. Distribuciones (Nivel académico y Género)
    niveles_raw = db.session.query(Egresados.nivel_maximo, func.count(Egresados.id_egresado))\
                            .filter(Egresados.id_egresado.in_(subq_egresados))\
                            .group_by(Egresados.nivel_maximo).all()
    niveles_labels = [n[0].capitalize() if n[0] else 'Sin registrar' for n in niveles_raw]
    niveles_data = [n[1] for n in niveles_raw]

    genero_map = {'M': 'Masculino', 'F': 'Femenino'}
    generos_raw = db.session.query(Egresados.genero, func.count(Egresados.id_egresado))\
                            .filter(Egresados.id_egresado.in_(subq_egresados), Egresados.genero.isnot(None))\
                            .group_by(Egresados.genero).all()
    genero_labels = [genero_map.get(g[0], 'Otro') for g in generos_raw]
    genero_data = [g[1] for g in generos_raw]

    # 5. Distribución por Sector Económico (Empleos actuales)
    sectores_raw = db.session.query(
        func.coalesce(Sectores.nombre, 'Sin sector').label('sector'),
        func.count(Empleos.id_empleo).label('total')
    ).select_from(Empleos)\
     .join(Empresas, Empleos.id_empresa == Empresas.id_empresa)\
     .outerjoin(Sectores, Empresas.id_sector == Sectores.id_sector)\
     .filter(Empleos.id_egresado.in_(subq_egresados), Empleos.es_actual == 1)\
     .group_by('sector')\
     .order_by(func.count(Empleos.id_empleo).desc())\
     .limit(7).all()

    sector_labels = [s[0] for s in sectores_raw]
    sector_data = [s[1] for s in sectores_raw]

    # 6. Evolución por año de egreso
    evolucion_raw = db.session.query(
        Egresados.anio_egreso,
        func.count(Egresados.id_egresado).label('egresados'),
        func.count(case((Egresados.es_bachiller == 1, 1))).label('bachiller'),
        func.count(case((Egresados.es_titulado == 1, 1))).label('titulado'),
        func.count(case((Egresados.tiene_maestria == 1, 1))).label('maestria'),
        func.count(case((Egresados.tiene_doctorado == 1, 1))).label('doctorado'),
        func.count(case((Egresados.tiene_phd == 1, 1))).label('phd')
    ).filter(Egresados.id_egresado.in_(subq_egresados), Egresados.anio_egreso.isnot(None))\
     .group_by(Egresados.anio_egreso).order_by(Egresados.anio_egreso).all()

    anios = [str(r.anio_egreso) for r in evolucion_raw]
    datos_anio = {
        'egresados': [r.egresados for r in evolucion_raw],
        'bachiller': [r.bachiller for r in evolucion_raw],
        'titulado': [r.titulado for r in evolucion_raw],
        'maestria': [r.maestria for r in evolucion_raw],
        'doctorado': [r.doctorado for r in evolucion_raw],
        'phd': [r.phd for r in evolucion_raw],
    }

    return {
        'total': total_egresados,
        'registrados': total_con_cuenta,
        'con_empleo_actual': con_empleo_actual,
        'tasa_empleabilidad': tasa_empleabilidad,
        'sin_empleo_reportado': sin_empleo_reportado,
        'bachilleres': bachilleres,
        'titulados': titulados,
        'niveles_labels': niveles_labels or ['Sin datos'],
        'niveles_data': niveles_data or [0],
        'genero_labels': genero_labels or ['Sin datos'],
        'genero_data': genero_data or [0],
        'sector_labels': sector_labels or ['Sin datos'],
        'sector_data': sector_data or [0],
        'anios': anios,
        'datos_anio': datos_anio
    }

@admin.route('/admin')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def dashboard():
    rol_activo = current_user.rol_activo_nombre()
    id_facultad = request.args.get('id_facultad', type=int)
    id_programa = request.args.get('id_programa', type=int)

    # Cada panel presenta el ámbito propio del rol; los filtros de un enlace
    # no pueden alterar los indicadores estructurales de la portada.
    metricas = obtener_metricas_dashboard(rol_activo, current_user.id_personal)
    plantilla = {
        'administrador': 'admin/panel_administrador.html',
        'utsag': 'admin/panel_utsag.html',
        'coordinador': 'admin/panel_coordinador.html',
        'docente_responsable': 'admin/panel_docente.html',
    }[rol_activo]
    contexto = construir_contexto_panel(rol_activo, current_user.id_personal, metricas)
    graficos = construir_analitica(rol_activo, current_user.id_personal)
    return render_template(plantilla, rol_activo=rol_activo, graficos=graficos, **metricas, **contexto)


@admin.route('/admin/informes/pdf')
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def informe_pdf():
    rol_activo = current_user.rol_activo_nombre()
    id_facultad = request.args.get('id_facultad', type=int)
    id_programa = request.args.get('id_programa', type=int)

    # Los filtros de URL no deben cambiar el encabezado ni el ámbito fuera de la asignación.
    alcance = _alcance_programas(rol_activo, current_user.id_personal)
    if alcance is not None:
        if id_programa and id_programa not in alcance:
            from flask import abort
            abort(403)
        if id_facultad and rol_activo == 'coordinador':
            if id_facultad not in _facultades_de_coordinador(current_user.id_personal):
                from flask import abort
                abort(403)
        elif id_facultad and rol_activo == 'docente_responsable':
            id_facultad = None
    datos = obtener_metricas_dashboard(rol_activo, current_user.id_personal, id_facultad, id_programa)

    # Determinar ámbito para el encabezado del reporte PDF
    ambito = None
    if id_programa:
        p = ProgramasEstudio.query.get(id_programa)
        ambito = p.nombre if p else None
    elif id_facultad:
        f = Facultades.query.get(id_facultad)
        ambito = f.nombre if f else None

    nombre_generador = (f"{current_user.personal.nombres} {current_user.personal.apellido_paterno}" if current_user.personal else current_user.correo)
    pdf_buffer = generar_informe_pdf(datos, nombre_generador, ambito=ambito)
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name='informe_egresados.pdf')

@admin.route('/admin/api/v11/indicadores', methods=['GET'])
@login_required
@requiere_rol('administrador', 'utsag', 'coordinador', 'docente_responsable')
def indicadores_v11_api():
    """Indicadores agregados, sin datos personales ni ampliación de permisos.

    Usa el mismo filtro de programas asignados que la página principal.
    No admite ids de facultad o programa manipulables en parámetros.
    """
    rol = current_user.rol_activo_nombre()
    datos = construir_analitica(rol, current_user.id_personal)
    res = jsonify({'ambito': 'Ingeniería de Sistemas y Computación',
                   'rol': rol, 'indicadores': datos})
    res.headers['Cache-Control'] = 'private, no-store'
    return res
