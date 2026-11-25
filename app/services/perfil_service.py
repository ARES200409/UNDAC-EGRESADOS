"""Cálculo real de completitud y etiquetas del perfil profesional del egresado."""

ETIQUETAS_SITUACION = {
    'empleado': 'Trabajando (dependiente)',
    'independiente': 'Trabajador independiente / Emprendedor',
    'desempleado': 'Actualmente sin empleo',
    'buscando': 'En búsqueda activa de empleo',
    'estudiando': 'Cursando estudios de posgrado / especialización',
    'no_especificado': 'No especificado',
}


def calcular_completitud_perfil(e):
    """Calcula el porcentaje de completitud del perfil usando solo datos reales en BD."""
    if not e:
        return {'porcentaje': 0, 'completados': 0, 'total': 8, 'faltantes': []}

    criterios = [
        ('Teléfono y correo de contacto', bool(e.telefono and (e.correo_personal or e.correo_institucional))),
        ('Ubicación de residencia', bool(e.distrito or e.provincia or e.region)),
        ('Título y resumen profesional', bool(e.titulo_cv and e.perfil_profesional)),
        ('Situación laboral actual', bool(e.situacion_laboral and e.situacion_laboral != 'no_especificado')),
        ('Experiencia laboral registrada', bool(e.empleos)),
        ('Formación académica adicional o grados', bool(e.trayectoria)),
        ('Habilidades profesionales', bool(e.habilidades)),
        ('Certificados o documentos cargados', bool(e.certificados or getattr(e, 'documentos_digitales', []))),
    ]

    completados = sum(1 for _, ok in criterios if ok)
    faltantes = [nombre for nombre, ok in criterios if not ok]
    total = len(criterios)
    porcentaje = round((completados / total) * 100)
    return {
        'porcentaje': porcentaje,
        'completados': completados,
        'total': total,
        'faltantes': faltantes,
    }
