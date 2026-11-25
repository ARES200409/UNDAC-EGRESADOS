"""KPI diferenciados para postulación interna y seguimiento externo autodeclarado."""
from flask import render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from app.admin import admin
from app.admin.helpers import requiere_rol, _alcance_programas
from app.extensions import db
from app.models import SeguimientoExterno, Postulaciones, Egresados, Curriculas
from app.utils.v8_db import tablas_v8_disponibles
from app.utils.v9_db import tablas_v9_disponibles

@admin.route('/admin/empleabilidad')
@login_required
@requiere_rol('administrador','utsag','coordinador','docente_responsable')
def empleabilidad():
    rol=current_user.rol_activo_nombre()
    alcance=_alcance_programas(rol,current_user.id_personal)
    externos={e:0 for e in ('visitado','postulado','entrevista','contratacion_reportada','no_seleccionado','desistio')}
    interna_total=0
    egresados_participantes=0
    disponible=tablas_v9_disponibles()
    if disponible:
        q=db.session.query(SeguimientoExterno.estado,func.count(SeguimientoExterno.id_seguimiento))            .join(Egresados,Egresados.id_egresado==SeguimientoExterno.id_egresado)            .join(Curriculas,Curriculas.id_curricula==Egresados.id_curricula)
        q_personas=db.session.query(func.count(func.distinct(SeguimientoExterno.id_egresado)))            .join(Egresados,Egresados.id_egresado==SeguimientoExterno.id_egresado)            .join(Curriculas,Curriculas.id_curricula==Egresados.id_curricula)
        if alcance is not None:
            q=q.filter(Curriculas.id_programa.in_(alcance))
            q_personas=q_personas.filter(Curriculas.id_programa.in_(alcance))
        externos.update({estado:int(n) for estado,n in q.group_by(SeguimientoExterno.estado).all()})
        egresados_participantes=q_personas.scalar() or 0
    if tablas_v8_disponibles():
        q=db.session.query(func.count(Postulaciones.id_postulacion))            .join(Egresados,Egresados.id_egresado==Postulaciones.id_egresado)            .join(Curriculas,Curriculas.id_curricula==Egresados.id_curricula)
        if alcance is not None:
            q=q.filter(Curriculas.id_programa.in_(alcance))
        interna_total=q.scalar() or 0
    return render_template('admin/empleabilidad.html',externos=externos,internas=interna_total,
                           participantes=egresados_participantes,disponible=disponible,rol_activo=rol)
