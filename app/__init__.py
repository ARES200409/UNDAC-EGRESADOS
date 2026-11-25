# app/__init__.py
from flask import Flask, render_template
from config import Config
from app.extensions import db, login_manager, bcrypt, mail
from flask_wtf.csrf import CSRFProtect, CSRFError

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Conexiones MySQL resilientes: no alterar la configuracion local del proyecto.
    opciones = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
    opciones.setdefault("pool_pre_ping", True)
    opciones.setdefault("pool_recycle", 280)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = opciones

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    # Registrar blueprints
    from app.auth import auth
    from app.egresado import egresado
    from app.admin import admin
    from app.public import public

    app.register_blueprint(auth)
    app.register_blueprint(egresado)
    app.register_blueprint(admin)
    app.register_blueprint(public)
    from app.asistente import asistente
    app.register_blueprint(asistente)
    from app.documentos import documentos
    app.register_blueprint(documentos)
    from app.empresa import empresa
    app.register_blueprint(empresa)
    from app.capacitaciones import capacitaciones
    app.register_blueprint(capacitaciones)

    # Módulo de registro inteligente por DNI
    from app.api_dni import api_dni
    from app.api_dni import routes as _  # noqa: F401
    app.register_blueprint(api_dni)

    # V11.2: endpoints de salud y trazabilidad no invasivos.
    from app.ops_v11_2 import ops
    from app.observabilidad_v11_2 import registrar_observabilidad
    app.register_blueprint(ops)
    registrar_observabilidad(app)

    @app.errorhandler(CSRFError)
    def error_csrf(e):
        from flask import flash, redirect, request, url_for
        flash("El formulario ha caducado o no es válido. Recarga la página e inténtalo nuevamente.", "warning")
        return redirect(request.referrer if request.referrer and request.referrer.startswith(request.host_url) else url_for("public.index"))

    @app.after_request
    def v11_cabeceras_seguridad(response):
        """Protección básica sin romper scripts/estilos existentes en V10.7.

        No se impone una CSP incompatible con los scripts inline anteriores.
        HTTPS y cookies Secure deben activarse en el despliegue final.
        """
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        from flask import request
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'private, no-store'
        if request.is_secure:
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
        return response

    # Manejo de errores personalizados
    @app.errorhandler(403)
    def acceso_restringido(e):
        return render_template('errores/403.html'), 403

    @app.errorhandler(404)
    def pagina_no_encontrada(e):
        return render_template('errores/404.html'), 404

    @app.errorhandler(500)
    def error_servidor(e):
        return render_template('errores/500.html'), 500

    # Filtro para formatear fechas
    @app.template_filter('format_date')
    def format_date(value):
        if not value:
            return 'Fecha no disponible'
        try:
            from datetime import datetime
            fecha = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return fecha.strftime('%d/%m/%Y')
        except Exception:
            return value

    @app.context_processor
    def contexto_foto_usuario():
        from flask_login import current_user
        from flask import url_for
        from app.auth.foto_cuenta import avatar_path
        from app.services.notificaciones_service import contar_no_leidas
        path = avatar_path(current_user)
        no_leidas = 0
        if getattr(current_user, 'is_authenticated', False):
            try:
                no_leidas = contar_no_leidas(current_user.id_usuario)
            except Exception:
                no_leidas = 0
        return {
            'foto_usuario_url': url_for('static', filename=path) if path else None,
            'notificaciones_no_leidas': no_leidas,
        }

    return app