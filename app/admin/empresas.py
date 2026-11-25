from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.admin import admin
from app.admin.helpers import requiere_rol
from app.extensions import db
from app.models import Empresas, Sectores

# Helper privado para procesar inputs del formulario sin repetir código
def _extraer_datos_empresa(form):
    return {
        'ruc': form.get('ruc', '').strip() or None,
        'razon_social': form.get('razon_social', '').strip(),
        'nombre_comercial': form.get('nombre_comercial', '').strip() or None,
        'id_sector': form.get('id_sector', type=int),
        'tipo_empresa': form.get('tipo_empresa', '').strip() or None,
        'direccion': form.get('direccion', '').strip() or None,
        'distrito': form.get('distrito', '').strip() or None,
        'provincia': form.get('provincia', '').strip() or None,
        'region': form.get('region', '').strip() or None,
        'pais': form.get('pais', '').strip() or 'Perú',
        'telefono': form.get('telefono', '').strip() or None,
        'sitio_web': form.get('sitio_web', '').strip() or None,
    }


@admin.route('/admin/empresas')
@login_required
@requiere_rol('administrador')
def empresas():
    buscar = request.args.get('buscar', '').strip()
    pagina = request.args.get('pagina', 1, type=int)

    # 1. Sugerencias pendientes
    pendientes = Empresas.query.filter_by(estado='pendiente').order_by(Empresas.id_empresa).all()

    # 2. Empresas activas
    q = Empresas.query.join(Empresas.sector, isouter=True).filter(Empresas.estado == 'activa')

    if buscar:
        like = f'%{buscar}%'
        q = q.filter(db.or_(
            Empresas.razon_social.ilike(like),
            Empresas.nombre_comercial.ilike(like),
            Empresas.ruc.ilike(like),
            Sectores.nombre.ilike(like)
        ))

    paginado = q.order_by(Empresas.razon_social).paginate(page=pagina, per_page=15, error_out=False)

    return render_template('admin/empresas.html',
                           pendientes=pendientes,
                           activas=paginado.items,
                           paginacion=paginado,
                           buscar=buscar,
                           pagina=pagina)


@admin.route('/admin/empresas/nueva', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador')
def nueva_empresa():
    sectores = Sectores.query.order_by(Sectores.nombre).all()

    if request.method == 'POST':
        datos = _extraer_datos_empresa(request.form)

        if datos['ruc']:
            existente = Empresas.query.filter_by(ruc=datos['ruc']).first()
            if existente:
                return render_template('admin/nueva_empresa.html',
                                       error_ruc=f'Este RUC ya pertenece a: {existente.nombre_display()}',
                                       empresa_existente=existente,
                                       sectores=sectores,
                                       form_data=request.form)

        empresa = Empresas(**datos, estado='activa')
        db.session.add(empresa)
        db.session.commit()
        flash('Empresa registrada correctamente.', 'success')
        return redirect(url_for('admin.empresas'))

    return render_template('admin/nueva_empresa.html', sectores=sectores, error_ruc=None, form_data=None)


@admin.route('/admin/empresas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_rol('administrador')
def editar_empresa(id):
    empresa = Empresas.query.get_or_404(id)
    sectores = Sectores.query.order_by(Sectores.nombre).all()

    if request.method == 'POST':
        datos = _extraer_datos_empresa(request.form)

        # Validar RUC único al editar si fue modificado
        if datos['ruc'] and datos['ruc'] != empresa.ruc:
            existente = Empresas.query.filter_by(ruc=datos['ruc']).first()
            if existente:
                return render_template('admin/editar_empresa.html',
                                       empresa=empresa,
                                       sectores=sectores,
                                       error_ruc=f'Este RUC ya pertenece a: {existente.nombre_display()}',
                                       form_data=request.form)

        # Actualizar campos directamente
        for clave, valor in datos.items():
            setattr(empresa, clave, valor)

        db.session.commit()
        flash('Empresa actualizada.', 'success')
        return redirect(url_for('admin.empresas'))

    return render_template('admin/editar_empresa.html', empresa=empresa, sectores=sectores, error_ruc=None, form_data=None)


@admin.route('/admin/empresas/<int:id>/accion', methods=['POST'])
@login_required
@requiere_rol('administrador')
def accion_empresa(id):
    empresa = Empresas.query.get_or_404(id)
    accion = request.form.get('accion')

    if accion == 'confirmar':
        empresa.estado = 'activa'
        db.session.commit()
        flash(f'Empresa "{empresa.nombre_display()}" confirmada.', 'success')
    else:
        flash('Acción no reconocida.', 'danger')

    return redirect(url_for('admin.empresas'))


@admin.route('/admin/empresas/buscar-ruc')
@login_required
@requiere_rol('administrador')
def buscar_ruc():
    ruc = request.args.get('ruc', '').strip()
    empresa = Empresas.query.filter_by(ruc=ruc).first()
    return jsonify({'existe': bool(empresa), 'nombre': empresa.nombre_display() if empresa else None})