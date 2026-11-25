# app/public/routes.py
from flask import render_template, redirect, url_for, request  # ← request importado
from app.public import public
from app.models import OfertasLaborales, Egresados, Curriculas
from app.extensions import db
from app.ambito import ids_programa_sistemas
from datetime import datetime, date
from app.utils.api_noticias import obtener_noticias_undac, formatear_fecha
import json
import requests
import re


# =======================================
# OFERTAS LABORALES
# =======================================
@public.route('/ofertas-laborales')
def ofertas():
    # Una visita pública no debe escribir en MySQL.
    lista = OfertasLaborales.query.filter(
        OfertasLaborales.activa == 1,
        OfertasLaborales.fecha_vencimiento >= date.today(),
    ).order_by(OfertasLaborales.fecha_publicacion.desc()).all()

    ofertas_json = json.dumps([{
        'id': o.id_oferta,
        'titulo': o.titulo,
        'empresa': o.nombre_empresa(),
        'telefono': o.telefono,
        'tipo_oferta': o.tipo_oferta,
        'jornada': o.jornada,
        'remuneracion': o.remuneracion,
        'modalidad': o.modalidad,
        'ubicacion': o.ubicacion,
        'descripcion': o.descripcion,
        'funciones': o.funciones,
        'requisitos': o.requisitos,
        'ruta_imagen': url_for('static', filename=o.ruta_imagen) if o.ruta_imagen else None,
        'url_original': o.url_original,
        'fecha_publicacion': o.fecha_publicacion.strftime('%d/%m/%Y') if o.fecha_publicacion else None,
        'fecha_vencimiento': o.fecha_vencimiento.strftime('%d/%m/%Y') if o.fecha_vencimiento else None,
    } for o in lista])

    portales = [
        {
            'titulo': 'Computrabajo',
            'subtitulo': 'Portal líder en Perú',
            'descripcion': 'Miles de ofertas diarias. Filtra por "Ingeniería de sistemas" en Pasco o Lima.',
            'url': 'https://pe.computrabajo.com/empleos-de-ingenieria-y-tecnico',
            'color': '#0073b1',
            'icono': 'bi-briefcase-fill'
        },
        {
            'titulo': 'Indeed Perú',
            'subtitulo': 'Motor de búsqueda global',
            'descripcion': 'Agrega ofertas de múltiples fuentes. Busca "sistemas" o "informática" en Pasco.',
            'url': 'https://pe.indeed.com/jobs?q=informatica+sistemas&l=Pasco',
            'color': '#2164f3',
            'icono': 'bi-search'
        },
        {
            'titulo': 'Bumeran',
            'subtitulo': 'Portal peruano',
            'descripcion': 'Popular entre empresas peruanas. Filtra por tecnología e informática.',
            'url': 'https://www.bumeran.com.pe/empleos-busqueda-informatica-sistemas.html',
            'color': '#e8a400',
            'icono': 'bi-person-workspace'
        },
        {
            'titulo': 'LinkedIn',
            'subtitulo': 'Red profesional global',
            'descripcion': 'Ideal para conectar con empresas. Busca "Ingeniero de sistemas" en Perú.',
            'url': 'https://www.linkedin.com/jobs/search/?keywords=ingeniero%20sistemas&location=Per%C3%BA',
            'color': '#0a66c2',
            'icono': 'bi-linkedin'
        },
        {
            'titulo': 'Universia',
            'subtitulo': 'Bolsa universitaria',
            'descripcion': 'Ofertas orientadas a universitarios y recién egresados de carreras técnicas.',
            'url': 'https://jobboard.universia.net/unheval_fiis?dateFrom=all&page=1',
            'color': '#00875a',
            'icono': 'bi-mortarboard-fill'
        },
        {
            'titulo': 'Aptitus',
            'subtitulo': 'Portal peruano',
            'descripcion': 'Ofertas de empresas peruanas con filtros por sector tecnológico y región.',
            'url': 'https://aptitus.com/empleos/pasco/tecnologia-sistemas',
            'color': '#c53030',
            'icono': 'bi-newspaper'
        }
    ]

    return render_template('public/ofertas.html', 
        ofertas=lista, 
        ofertas_json=ofertas_json,
        portales=portales,
        anio=date.today().year
    )

# =======================================
# ALIAS PARA OFERTAS (URL más amigable)
# =======================================
@public.route('/ofertas')
def ofertas_redirect():
    return redirect(url_for('public.ofertas'))

# =======================================
# PAGINA DE INICIO
# =======================================
@public.route('/')
def index():
    alcance = ids_programa_sistemas()
    q = Egresados.query.join(Curriculas, Egresados.id_curricula == Curriculas.id_curricula)
    if alcance is not None:
        q = q.filter(Curriculas.id_programa.in_(alcance))
    total_egresados = q.count()
    ofertas_count = OfertasLaborales.query.filter_by(activa=1).count()
    return render_template('public/index.html',
        total_egresados=total_egresados,
        ofertas=ofertas_count,
        anio=date.today().year
    )

# =======================================
# PAGINA DE QUIENES SOMOS
# =======================================
@public.route('/quienes-somos')
def quienes_somos():
    return render_template('public/quienes_somos.html', 
        anio=date.today().year
    )

# =======================================
# PAGINA DE NOTICIAS
# =======================================
@public.route('/noticias')
def noticias():
    # Obtener el número de página desde la URL (ej: ?page=2)
    pagina = request.args.get('page', 1, type=int)
    if pagina < 1:
        pagina = 1
    
    # Llamar a la API con la página solicitada
    noticias_raw = obtener_noticias_undac(pagina)
    
    # Procesar noticias
    noticias_procesadas = []
    for n in noticias_raw:
        # Limpiar la descripción de etiquetas HTML
        descripcion_raw = n.get('description', '')
        if descripcion_raw:
            # Eliminar etiquetas HTML y decodificar entidades
            descripcion_limpia = re.sub(r'<[^>]+>', '', descripcion_raw)
            descripcion_limpia = descripcion_limpia.replace('&Oacute;', 'Ó')
            descripcion_limpia = descripcion_limpia.replace('&oacute;', 'ó')
            descripcion_limpia = descripcion_limpia.replace('&Aacute;', 'Á')
            descripcion_limpia = descripcion_limpia.replace('&aacute;', 'á')
            descripcion_limpia = descripcion_limpia.replace('&Eacute;', 'É')
            descripcion_limpia = descripcion_limpia.replace('&eacute;', 'é')
            descripcion_limpia = descripcion_limpia.replace('&Iacute;', 'Í')
            descripcion_limpia = descripcion_limpia.replace('&iacute;', 'í')
            descripcion_limpia = descripcion_limpia.replace('&Uacute;', 'Ú')
            descripcion_limpia = descripcion_limpia.replace('&uacute;', 'ú')
            descripcion_limpia = descripcion_limpia.replace('&Ntilde;', 'Ñ')
            descripcion_limpia = descripcion_limpia.replace('&ntilde;', 'ñ')
        else:
            descripcion_limpia = ''
        
        noticias_procesadas.append({
            'titulo': n.get('title', 'Sin título'),
            'fecha': formatear_fecha(n.get('created_at')),
            'enlace': f"https://undac.edu.pe/noticias/{n.get('slug', n.get('id'))}",
            'imagen': n.get('image_url', '') or n.get('image_path', ''),
            'categoria': n.get('type', 'Noticia'),
            'resumen': descripcion_limpia[:180]  # Limpiado y truncado
        })
    
    # Obtener total de páginas (lo devuelve la API)
    # Por ahora, asumimos que hay más páginas si hay 9 noticias
    total_paginas = 2 if len(noticias_raw) == 9 else 1
    
    return render_template('public/noticias.html',
        noticias=noticias_procesadas,
        total=len(noticias_procesadas),
        pagina_actual=pagina,
        total_paginas=total_paginas,
        fecha_actualizacion=datetime.now().strftime('%d/%m/%Y %H:%M'),
        anio=date.today().year
    )