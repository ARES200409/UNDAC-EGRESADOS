"""Informe institucional de seguimiento de egresados (NEXO UNDAC).

Solo consume datos agregados previamente filtrados por permisos en dashboard.py.
No infiere desempleo a partir de la ausencia de información laboral.
Compatible con Python/ReportLab instalados por requirements.txt.
"""
from datetime import datetime
import io
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

AZUL = colors.HexColor('#073C7A')
MARINO = colors.HexColor('#07264A')
CELESTE = colors.HexColor('#07B7E9')
CELESTE_CLARO = colors.HexColor('#E8F7FF')
FONDO = colors.HexColor('#F2F8FD')
TEXTO = colors.HexColor('#17314C')
SECUNDARIO = colors.HexColor('#526D87')
LINEA = colors.HexColor('#D7E7F2')
VERDE = colors.HexColor('#0B806E')

_DIR_IMAGENES = Path(__file__).resolve().parents[1] / 'static' / 'img'


def _estilos():
    return {
        'eyebrow': ParagraphStyle('NEyebrow', fontName='Helvetica-Bold', fontSize=8.1,
                                  leading=11, textColor=AZUL, spaceAfter=6),
        'titulo': ParagraphStyle('NTitulo', fontName='Helvetica-Bold', fontSize=20,
                                leading=24, textColor=MARINO, spaceAfter=8),
        'sub': ParagraphStyle('NSub', fontName='Helvetica', fontSize=9,
                             leading=13, textColor=SECUNDARIO, spaceAfter=13),
        'h2': ParagraphStyle('NH2', fontName='Helvetica-Bold', fontSize=11.6,
                            leading=15, textColor=MARINO, spaceBefore=15, spaceAfter=7),
        'body': ParagraphStyle('NBody', fontName='Helvetica', fontSize=8.6,
                              leading=13.3, textColor=TEXTO),
        'small': ParagraphStyle('NSmall', fontName='Helvetica', fontSize=7.7,
                               leading=11.5, textColor=SECUNDARIO),
        'smallbold': ParagraphStyle('NSmallBold', fontName='Helvetica-Bold', fontSize=7.8,
                                   leading=11.5, textColor=MARINO),
        'metahead': ParagraphStyle('NMetaHead', fontName='Helvetica-Bold', fontSize=7,
                                  leading=10.3, textColor=AZUL),
        'meta': ParagraphStyle('NMeta', fontName='Helvetica', fontSize=8,
                              leading=11.3, textColor=TEXTO),
        'k-label': ParagraphStyle('NKLabel', fontName='Helvetica-Bold', fontSize=7,
                                 leading=10, textColor=SECUNDARIO),
        'k-value': ParagraphStyle('NKValue', fontName='Helvetica-Bold', fontSize=19,
                                 leading=23, textColor=AZUL),
        'k-note': ParagraphStyle('NKNote', fontName='Helvetica', fontSize=7.0,
                                leading=9.5, textColor=SECUNDARIO),
        'table-h': ParagraphStyle('NTblH', fontName='Helvetica-Bold', fontSize=8,
                                 leading=11, textColor=colors.white),
        'table-l': ParagraphStyle('NTblL', fontName='Helvetica', fontSize=8.1,
                                 leading=11.4, textColor=TEXTO),
        'table-v': ParagraphStyle('NTblV', fontName='Helvetica-Bold', fontSize=8.5,
                                 leading=11.4, textColor=AZUL),
    }


def _entero(n):
    try:
        return max(0, int(n or 0))
    except (TypeError, ValueError, OverflowError):
        return 0


def _porcentaje(n, d):
    return f'{100 * n / d:.1f} %' if d else 'N/D'


def _esc(v):
    return escape('' if v is None else str(v))


def _card(label, valor, detalle, width, S):
    bloque = [
        Paragraph(_esc(label).upper(), S['k-label']),
        Spacer(1, 5),
        Paragraph(_esc(valor), S['k-value']),
        Spacer(1, 2),
        Paragraph(_esc(detalle), S['k-note']),
    ]
    t = Table([[bloque]], colWidths=[width], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), FONDO),
        ('BOX', (0, 0), (-1, -1), .65, LINEA),
        ('LINEABOVE', (0, 0), (-1, 0), 3, CELESTE),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 11),
        ('RIGHTPADDING', (0, 0), (-1, -1), 9),
    ]))
    return t


def _encabezado(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(MARINO)
    canvas.rect(0, h - 78, w, 78, fill=1, stroke=0)
    canvas.setFillColor(CELESTE)
    canvas.rect(0, h - 81, w, 3, fill=1, stroke=0)
    logo = _DIR_IMAGENES / 'logo_undac_original.png'
    if logo.is_file():
        canvas.setFillColor(colors.white)
        canvas.roundRect(38, h - 64, 46, 46, 8, fill=1, stroke=0)
        try:
            canvas.drawImage(str(logo), 45, h - 60, width=32, height=37,
                             preserveAspectRatio=True, anchor='c', mask='auto')
        except Exception:
            pass
    sistemas = _DIR_IMAGENES / 'logo_sistemas_original.png'
    if sistemas.is_file():
        try:
            canvas.drawImage(str(sistemas), w - 220, h - 60, width=36, height=36,
                             preserveAspectRatio=True, anchor='c', mask='auto')
        except Exception:
            pass
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 12.2)
    canvas.drawString(95, h - 38, 'NEXO UNDAC')
    canvas.setFillColor(colors.HexColor('#BFEAFF'))
    canvas.setFont('Helvetica', 8.3)
    canvas.drawString(95, h - 53, 'INGENIERÍA DE SISTEMAS Y COMPUTACIÓN')
    canvas.setFillColor(colors.HexColor('#E2F3FF'))
    canvas.setFont('Helvetica-Bold', 7.2)
    canvas.drawRightString(w - 39, h - 33, 'INFORME INSTITUCIONAL')
    canvas.setFont('Helvetica', 7)
    canvas.drawRightString(w - 39, h - 47, 'Seguimiento de egresados')

    canvas.setStrokeColor(LINEA)
    canvas.line(39, 39, w - 39, 39)
    canvas.setFont('Helvetica', 7.3)
    canvas.setFillColor(SECUNDARIO)
    canvas.drawString(39, 25, 'NEXO UNDAC  |  Datos agregados del ámbito autorizado')
    canvas.drawRightString(w - 39, 25, f'Página {doc.page}')
    canvas.restoreState()


def _bloque_metadatos(ambito, fecha, nombre, ancho, S):
    items = [('ÁMBITO ACADÉMICO', ambito), ('EMISIÓN', fecha), ('RESPONSABLE', nombre)]
    widths = [ancho * .43, ancho * .22, ancho * .35]
    contenidos = [[Paragraph(a, S['metahead']), Spacer(1, 3), Paragraph(_esc(b), S['meta'])]
                  for a, b in items]
    t = Table([contenidos], colWidths=widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CELESTE_CLARO),
        ('BOX', (0, 0), (-1, -1), .6, LINEA),
        ('LINEBEFORE', (1, 0), (-1, -1), .6, LINEA),
        ('LEFTPADDING', (0, 0), (-1, -1), 11),
        ('RIGHTPADDING', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def _tabla_indicadores(filas, ancho, S):
    celdas = [[Paragraph('INDICADOR', S['table-h']), Paragraph('VALOR', S['table-h'])]]
    celdas.extend([[Paragraph(_esc(k), S['table-l']), Paragraph(_esc(v), S['table-v'])]
                    for k, v in filas])
    t = Table(celdas, colWidths=[ancho * .77, ancho * .23], hAlign='LEFT', repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, FONDO]),
        ('LINEBELOW', (0, 1), (-1, -1), .45, LINEA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def _nota_resaltada(titulo, texto, ancho, S, fondo=CELESTE_CLARO):
    contenido = [Paragraph(_esc(titulo), S['smallbold']), Spacer(1, 4), Paragraph(_esc(texto), S['small'])]
    tb = Table([[contenido]], colWidths=[ancho])
    tb.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), fondo),
        ('LINEBEFORE', (0, 0), (0, 0), 3, CELESTE),
        ('TOPPADDING', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 11),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return tb


def _data_pairs(labels, values):
    pares = []
    for label, valor in zip(labels or [], values or []):
        n = _entero(valor)
        if n:
            pares.append((str(label), n))
    return pares


def _grafico_dona(labels, values, titulo):
    pares = _data_pairs(labels, values)
    if not pares:
        return None
    fig, ax = plt.subplots(figsize=(5.6, 3.4), dpi=130)
    try:
        paleta = ['#0E67B4', '#02B6C9', '#69B4F6', '#287B78', '#8AA8C2', '#1F4B7A']
        ax.pie([p[1] for p in pares], startangle=90,
               colors=[paleta[i % len(paleta)] for i in range(len(pares))],
               wedgeprops={'width': .35, 'edgecolor': '#FFFFFF', 'linewidth': 2})
        ax.text(0, 0, str(sum(p[1] for p in pares)), ha='center', va='center',
                fontsize=18, fontweight='bold', color='#073C7A')
        ax.set_title(titulo, fontweight='bold', fontsize=11, color='#07264A', pad=13)
        fig.legend([p[0] for p in pares], loc='lower center', ncol=2,
                   fontsize=7, frameon=False, bbox_to_anchor=(.5, -.08))
        fig.tight_layout(rect=[0, .08, 1, 1])
        b = io.BytesIO(); fig.savefig(b, format='png', bbox_inches='tight', dpi=130)
        b.seek(0); return b
    finally:
        plt.close(fig)


def _grafico_barras(labels, values, titulo):
    pares = _data_pairs(labels, values)[:7]
    if not pares:
        return None
    fig, ax = plt.subplots(figsize=(8.5, 3.3), dpi=130)
    try:
        ax.barh([p[0] for p in pares], [p[1] for p in pares], color='#1B86D1')
        ax.invert_yaxis()
        ax.set_title(titulo, fontsize=11, fontweight='bold', color='#07264A', pad=13)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.grid(axis='x', color='#DCEBF7', alpha=.85)
        ax.set_axisbelow(True)
        ax.tick_params(axis='y', length=0, labelsize=8)
        ax.tick_params(axis='x', labelsize=8)
        fig.tight_layout()
        b = io.BytesIO(); fig.savefig(b, format='png', bbox_inches='tight', dpi=130)
        b.seek(0); return b
    finally:
        plt.close(fig)


def _grafico_linea(anios, series):
    pares = _data_pairs(anios, (series or {}).get('egresados', []))
    if not pares:
        return None
    fig, ax = plt.subplots(figsize=(9, 3.0), dpi=130)
    try:
        x = range(len(pares))
        ax.plot(x, [p[1] for p in pares], color='#098BCB', marker='o', linewidth=2.5)
        ax.fill_between(x, [p[1] for p in pares], color='#A8E6FA', alpha=.36)
        ax.set_xticks(list(x), [p[0] for p in pares], fontsize=8)
        ax.yaxis.get_major_locator().set_params(integer=True)
        ax.grid(axis='y', color='#DCEBF7')
        ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
        ax.set_title('Egresados por año de egreso', fontsize=11, fontweight='bold', color='#07264A', pad=10)
        fig.tight_layout()
        b = io.BytesIO(); fig.savefig(b, format='png', bbox_inches='tight', dpi=130)
        b.seek(0); return b
    finally:
        plt.close(fig)


def generar_informe_pdf(datos, generado_por, ambito=None):
    """Devuelve un archivo PDF en memoria; la consulta SQL/roles permanece intacta."""
    datos = datos or {}
    total = _entero(datos.get('total'))
    registrados = _entero(datos.get('registrados'))
    con_empleo = _entero(datos.get('con_empleo_actual'))
    sin_empleo_declarado = max(0, registrados - con_empleo)
    bachilleres = _entero(datos.get('bachilleres'))
    titulados = _entero(datos.get('titulados'))
    fecha = datetime.now().strftime('%d/%m/%Y · %H:%M')
    nombre = str(generado_por or 'Usuario autorizado')
    dominio = str(ambito or 'Ingeniería de Sistemas y Computación (ámbito autorizado)')
    tasa_cobertura = _porcentaje(registrados, total)
    tasa_reporte = _porcentaje(con_empleo, registrados)
    S = _estilos()
    ancho = A4[0] - 36 * mm

    salida = io.BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=31 * mm, bottomMargin=20 * mm,
                            title='Informe institucional de seguimiento - NEXO UNDAC',
                            author='NEXO UNDAC - Ingeniería de Sistemas y Computación')
    historia = [
        Paragraph('REPORTE DE SEGUIMIENTO · SISTEMAS', S['eyebrow']),
        Paragraph('Indicadores académicos y laborales', S['titulo']),
        Paragraph('Resumen institucional de la información incorporada al sistema. '
                  'Los resultados corresponden únicamente al ámbito autorizado y la fecha de consulta.', S['sub']),
        _bloque_metadatos(dominio, fecha, nombre, ancho, S),
        Spacer(1, 12),
    ]

    espacio = 8
    ancho_caja = (ancho - 3*espacio) / 4
    kpis = [
        ('PADRÓN', str(total), 'Egresados incorporados'),
        ('CON CUENTA', str(registrados), 'Cuentas vinculadas'),
        ('EMPLEO DECLARADO', str(con_empleo), 'Cuentas con reporte actual'),
        ('COBERTURA', tasa_cobertura, 'Con cuenta / padrón'),
    ]
    kpi_widgets = [_card(a, b, c, ancho_caja, S) for a, b, c in kpis]
    kpi_table = Table([[widget for widget in kpi_widgets]],
                      colWidths=[ancho_caja + (espacio if i < 3 else 0) for i in range(4)])
    kpi_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), espacio),
        ('RIGHTPADDING', (3, 0), (3, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    historia += [kpi_table,
                Paragraph('01  /  Resultados del registro', S['h2'])]

    filas = [
        ('Egresados incorporados al padrón de Sistemas', total),
        ('Cuentas vinculadas a egresados', registrados),
        ('Cobertura de cuentas sobre el padrón', tasa_cobertura),
        ('Cuentas con empleo actual declarado', con_empleo),
        ('Proporción de cuentas con empleo declarado', tasa_reporte),
        ('Cuentas sin empleo actual informado', sin_empleo_declarado),
        ('Egresados registrados como bachilleres', bachilleres),
        ('Egresados registrados como titulados', titulados),
    ]
    historia += [_tabla_indicadores(filas, ancho, S),
                 Paragraph('02  /  Lectura responsable de los datos', S['h2'])]

    if total == 0:
        lectura = ('No hay egresados incorporados al padrón local para este ámbito. '
                   'Una verificación satisfactoria en la API académica no incorpora automáticamente '
                   'una cuenta ni un egresado al registro local. Con padrón vacío, la cobertura '
                   'y las proporciones laborales no son calculables.')
    elif registrados == 0:
        lectura = (f'El padrón contiene {total} egresado(s), pero todavía no hay cuentas vinculadas '
                   'dentro del ámbito consultado. Es necesario completar el registro voluntario '
                   'para disponer de seguimiento laboral y encuestas.')
    else:
        lectura = (f'En el ámbito consultado se registran {registrados} cuentas vinculadas '
                   f'a {total} egresado(s). De esas cuentas, {con_empleo} tienen un empleo '
                   'actual declarado. No registrar empleo no demuestra desempleo.')
    historia += [_nota_resaltada('INTERPRETACIÓN DEL RESULTADO', lectura, ancho, S),
                 Spacer(1, 9),
                 Paragraph('Fuente: base de datos local de NEXO UNDAC. Los indicadores reflejan '
                           'registros disponibles, no un censo de todos los egresados de la universidad.', S['small'])]

    graficos = [
        (_grafico_dona(datos.get('niveles_labels', []), datos.get('niveles_data', []), 'Nivel académico'), 'Nivel académico'),
        (_grafico_dona(datos.get('genero_labels', []), datos.get('genero_data', []), 'Género registrado'), 'Género'),
    ]
    sectores = _grafico_barras(datos.get('sector_labels', []), datos.get('sector_data', []),
                               'Empleos actuales por sector')
    evolucion = _grafico_linea(datos.get('anios', []), datos.get('datos_anio', {}))
    hay_graficos = any(g is not None for g, _ in graficos) or sectores is not None or evolucion is not None
    if hay_graficos:
        historia += [PageBreak(), Paragraph('03  /  Visualizaciones del padrón', S['h2']),
                     Paragraph('Gráficos elaborados solo cuando la consulta devuelve datos positivos. '
                               'Las categorías sin registros no se representan como resultados negativos.', S['small']),
                     Spacer(1, 10)]
        presentes = [g for g, _ in graficos if g]
        if presentes:
            if len(presentes) == 2:
                tb = Table([[Image(presentes[0], width=78*mm, height=52*mm, kind='proportional'),
                             Image(presentes[1], width=78*mm, height=52*mm, kind='proportional')]],
                           colWidths=[ancho/2, ancho/2])
                tb.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                                        ('LEFTPADDING', (0,0), (-1,-1), 0),
                                        ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
                historia += [tb, Spacer(1, 6)]
            else:
                historia += [Image(presentes[0], width=91*mm, height=56*mm, kind='proportional'), Spacer(1, 5)]
        if evolucion:
            historia += [Paragraph('Evolución por promoción', S['h2']),
                         Image(evolucion, width=ancho, height=62*mm, kind='proportional'), Spacer(1, 7)]
        if sectores:
            historia += [Paragraph('Vinculación laboral declarada', S['h2']),
                         Image(sectores, width=ancho, height=62*mm, kind='proportional'), Spacer(1, 8)]
        historia += [Paragraph('Nota: los empleos corresponden a información declarada. '
                              'Los recuentos por sector representan registros de empleo y no '
                              'necesariamente personas distintas.', S['small'])]

    doc.build(historia, onFirstPage=_encabezado, onLaterPages=_encabezado)
    salida.seek(0)
    return salida
