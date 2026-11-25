"""Fotografía de cuenta local. Independiente de migraciones de MySQL.
Los archivos se convierten a WEBP para eliminar metadatos del original.
"""
import os
import secrets
import hmac
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from flask import current_app, request, render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.auth import auth
from app.extensions import db

MAX_UPLOAD_BYTES = 3 * 1024 * 1024


def avatar_path(usuario):
    if not getattr(usuario, 'is_authenticated', False):
        return None
    path = Path(current_app.static_folder) / 'uploads' / 'avatars' / f'user_{int(usuario.id_usuario)}.webp'
    if path.is_file():
        return f'uploads/avatars/user_{int(usuario.id_usuario)}.webp'
    if usuario.id_egresado and usuario.egresado and usuario.egresado.foto:
        return usuario.egresado.foto
    return None


def avatar_csrf():
    if 'csrf_foto_cuenta' not in session:
        session['csrf_foto_cuenta'] = secrets.token_urlsafe(32)
    return session['csrf_foto_cuenta']


@auth.route('/mi-cuenta', methods=['GET', 'POST'])
@login_required
def mi_cuenta():
    if request.method == 'POST':
        if not hmac.compare_digest(str(request.form.get('csrf_foto', '')), str(session.get('csrf_foto_cuenta', '__invalid__'))):
            flash('Sesión de formulario no válida. Actualiza la página.', 'danger')
            return redirect(url_for('auth.mi_cuenta'))
        foto = request.files.get('foto')
        if not foto or not foto.filename:
            flash('Selecciona una fotografía JPG, PNG o WEBP.', 'warning')
            return redirect(url_for('auth.mi_cuenta'))
        content = foto.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            flash('La imagen no puede superar los 3 MB.', 'warning')
            return redirect(url_for('auth.mi_cuenta'))
        try:
            from io import BytesIO
            with Image.open(BytesIO(content)) as source:
                if source.format not in ('JPEG', 'PNG', 'WEBP'):
                    raise ValueError('Formato no permitido')
                if source.width * source.height > 20_000_000:
                    raise ValueError('Resolución de imagen excesiva')
                source.load()
                img = ImageOps.exif_transpose(source).convert('RGB')
                img = ImageOps.fit(img, (420, 420), method=Image.Resampling.LANCZOS)
                folder = Path(current_app.static_folder) / 'uploads' / 'avatars'
                folder.mkdir(parents=True, exist_ok=True)
                tmp = folder / f'.avatar_{int(current_user.id_usuario)}_{secrets.token_hex(8)}.webp'
                img.save(tmp, 'WEBP', quality=86, method=4)
                dest = folder / f'user_{int(current_user.id_usuario)}.webp'
                os.replace(tmp, dest)
            if current_user.id_egresado and current_user.egresado:
                current_user.egresado.foto = f'uploads/avatars/user_{int(current_user.id_usuario)}.webp'
                db.session.commit()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            flash('No se pudo procesar la imagen. Prueba con una fotografía válida.', 'danger')
            return redirect(url_for('auth.mi_cuenta'))
        flash('Fotografía de perfil actualizada.', 'success')
        return redirect(url_for('auth.mi_cuenta'))
    return render_template('auth/mi_cuenta.html', token_foto=avatar_csrf())
