"""Seguimiento externo declarado: un clic NO equivale a una postulación ni contratación."""
from datetime import date, datetime, timezone
from ipaddress import ip_address
from urllib.parse import urlsplit
from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.egresado import egresado
from app.extensions import db
from app.models import OfertasLaborales, Postulaciones, SeguimientoExterno, AutorizacionesDocumentales
from app.services.auditoria_service import registrar_auditoria
from app.utils.v8_db import tablas_v8_disponibles
from app.utils.v9_db import tablas_v9_disponibles
from app.egresado.routes import solo_egresado

ESTADOS = {
 'visitado': 'Solo consulté el enlace',
 'postulado': 'Envié mi postulación',
 'entrevista': 'Participé en una entrevista',
 'contratacion_reportada': 'Conseguí el empleo (declarado)',
 'no_seleccionado': 'No fui seleccionado',
 'desistio': 'No continuaré con esta vacante',
}

def url_externa_segura(url):
    """Solo links HTTPS a hosts públicos. No hace requests a la URL."""
    try:
        info = urlsplit((url or '').strip())
        host = (info.hostname or '').lower().rstrip('.')
        if info.scheme != 'https' or not host or not info.netloc or info.username or info.password:
            return False
        if host in ('localhost','127.0.0.1','0.0.0.0') or host.endswith(('.localhost','.local','.internal')):
            return False
        try:
            ip = ip_address(host)
            if not ip.is_global:
                return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False

@egresado.route('/ofertas/<int:id_oferta>/salir')
@login_required
@solo_egresado
def salir_a_oferta(id_oferta):
    oferta = OfertasLaborales.query.get_or_404(id_oferta)
    if not oferta.url_original or not url_externa_segura(oferta.url_original):
        abort(400, 'Esta oferta no contiene un enlace externo HTTPS válido.')
    if not oferta.activa or oferta.fecha_vencimiento < date.today():
        flash('Esta convocatoria ya no está vigente.', 'warning')
        return redirect(url_for('egresado.ofertas'))
    if tablas_v9_disponibles():
        seg = SeguimientoExterno.query.filter_by(id_egresado=current_user.id_egresado,id_oferta=oferta.id_oferta).first()
        if not seg:
            seg = SeguimientoExterno(id_egresado=current_user.id_egresado, id_oferta=oferta.id_oferta,
                                     estado='visitado', visitas=0)
            db.session.add(seg)
        seg.visitas = (seg.visitas or 0) + 1
        db.session.commit()
    # Redirige sin afirmar que la postulación realmente fue enviada.
    return redirect(oferta.url_original.strip(), code=302)

@egresado.route('/mis-postulaciones')
@login_required
@solo_egresado
def mi_seguimiento():
    externas = []
    internas = []
    v9 = tablas_v9_disponibles()
    if v9:
        externas = SeguimientoExterno.query.filter_by(id_egresado=current_user.id_egresado)            .order_by(SeguimientoExterno.actualizado_en.desc()).all()
    if tablas_v8_disponibles():
        internas = Postulaciones.query.filter_by(id_egresado=current_user.id_egresado)            .order_by(Postulaciones.fecha.desc()).all()
    return render_template('egresado/mi_seguimiento.html', externas=externas, internas=internas,
                           estados=ESTADOS, migracion_v9=v9)

@egresado.route('/mis-postulaciones/externa/<int:id_seguimiento>/actualizar', methods=['POST'])
@login_required
@solo_egresado
def actualizar_seguimiento(id_seguimiento):
    if not tablas_v9_disponibles():
        flash('Se requiere ejecutar la migración V9.', 'warning')
        return redirect(url_for('egresado.mi_seguimiento'))
    seg = SeguimientoExterno.query.filter_by(
        id_seguimiento=id_seguimiento, id_egresado=current_user.id_egresado).first_or_404()
    estado = request.form.get('estado', '').strip()
    if estado not in ESTADOS:
        abort(400)
    obs = request.form.get('observacion', '').strip()[:500]
    seg.estado = estado
    seg.observacion = obs or None
    if estado == 'postulado' and not seg.fecha_postulacion:
        seg.fecha_postulacion = date.today()
    if estado == 'contratacion_reportada' and not seg.fecha_contratacion:
        seg.fecha_contratacion = date.today()
    db.session.commit()
    flash('Actualización guardada. Este resultado es declarado por ti y no verificado por la empresa.', 'success')
    return redirect(url_for('egresado.mi_seguimiento'))


@egresado.route('/mis-postulaciones/interna/<int:id_postulacion>/retirar', methods=['POST'])
@login_required
@solo_egresado
def retirar_postulacion(id_postulacion):
    post = Postulaciones.query.filter_by(
        id_postulacion=id_postulacion, id_egresado=current_user.id_egresado
    ).first_or_404()
    if post.estado == 'retirada':
        flash('La postulación ya fue retirada.', 'info')
        return redirect(url_for('egresado.mi_seguimiento'))

    post.estado = 'retirada'
    post.actualizado_en = datetime.now(timezone.utc).replace(tzinfo=None)
    AutorizacionesDocumentales.query.filter_by(
        id_postulacion=post.id_postulacion, id_egresado=current_user.id_egresado, autorizado=1
    ).update({'autorizado': 0, 'revocado_en': datetime.now(timezone.utc).replace(tzinfo=None)})
    db.session.commit()
    registrar_auditoria('retirar_postulacion', 'bolsa_laboral', 'postulaciones', post.id_postulacion)
    flash('Postulación retirada y acceso documental revocado.', 'info')
    return redirect(url_for('egresado.mi_seguimiento'))
