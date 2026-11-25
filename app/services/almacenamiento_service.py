"""Servicio de almacenamiento documental privado fuera de app/static.

Garantiza:
- Almacenamiento fuera del directorio público estático.
- Lista blanca estricta de extensiones y validación de firma binaria (magic bytes).
- Rechazo de extensiones dobles sospechosas o archivos vacíos/excedidos.
- Nombres internos aleatorios sin datos sensibles.
- Prevención de Path Traversal mediante os.path.commonpath.
- Cálculo de huella SHA-256 para integridad y auditoría.
"""

import hashlib
import os
import re
import secrets
from dataclasses import dataclass
from flask import current_app
from werkzeug.utils import secure_filename

EXTENSIONES_DOCUMENTO_PRIVADO = {'pdf', 'jpg', 'jpeg', 'png'}

MIME_POR_EXTENSION = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
}

_EXTENSIONES_PELIGROSAS = {
    'exe', 'bat', 'cmd', 'com', 'ps1', 'sh', 'php', 'py', 'js',
    'vbs', 'msi', 'dll', 'scr', 'pif', 'jar', 'html', 'htm', 'svg',
}


@dataclass(frozen=True)
class ResultadoAlmacenamiento:
    """Metadatos devueltos tras guardar un archivo en almacenamiento privado."""

    nombre_original: str
    nombre_interno: str
    ruta_relativa: str
    extension: str
    mime_type: str
    tamano_bytes: int
    sha256: str


def obtener_raiz_privada():
    """Devuelve la ruta absoluta normalizada del directorio privado."""
    raiz = current_app.config.get('PRIVATE_STORAGE_DIR')
    if not raiz:
        raiz = os.path.join(current_app.instance_path, 'storage_privado')
    return os.path.abspath(raiz)


def firma_binaria_valida(cabecera, extension):
    """Valida los magic bytes reales del archivo contra la extensión declarada."""
    if not cabecera:
        return False
    if extension == 'pdf':
        return cabecera.startswith(b'%PDF-')
    if extension == 'png':
        return cabecera.startswith(b'\x89PNG\r\n\x1a\n')
    if extension in ('jpg', 'jpeg'):
        return cabecera.startswith(b'\xff\xd8\xff')
    return False


def resolver_ruta_privada(ruta_relativa):
    """Resuelve una ruta relativa dentro del almacenamiento privado evitando traversal."""
    if not ruta_relativa:
        return None
    texto = str(ruta_relativa).replace('\\', '/')
    if texto.startswith('/') or os.path.isabs(texto) or ':' in texto:
        return None
    if '..' in texto.split('/'):
        return None
    raiz = obtener_raiz_privada()
    candidata = os.path.abspath(os.path.join(raiz, texto))
    if os.path.commonpath((raiz, candidata)) != raiz:
        return None
    return candidata


def guardar_documento_privado(archivo, subcarpeta='documentos', limite_bytes=None):
    """Valida y guarda un archivo en PRIVATE_STORAGE_DIR.

    Lanza ValueError con mensaje seguro para el usuario ante archivos inválidos.
    """
    if not archivo or not getattr(archivo, 'filename', ''):
        raise ValueError('No se seleccionó ningún archivo.')

    subcarpeta = str(subcarpeta or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', subcarpeta):
        raise ValueError('Categoría de almacenamiento inválida.')

    nombre_seguro = secure_filename(archivo.filename)
    if not nombre_seguro or '.' not in nombre_seguro:
        raise ValueError('El archivo debe tener una extensión válida (PDF, JPG o PNG).')

    partes = [p.lower() for p in nombre_seguro.split('.')]
    if len(partes) > 2 and any(p in _EXTENSIONES_PELIGROSAS for p in partes[:-1]):
        raise ValueError('Nombre de archivo no permitido por seguridad.')

    extension = partes[-1]
    if extension not in EXTENSIONES_DOCUMENTO_PRIVADO:
        raise ValueError('Formato no permitido. Solo se aceptan PDF, JPG y PNG.')

    max_bytes = int(limite_bytes or current_app.config.get('MAX_DOCUMENT_BYTES', 10 * 1024 * 1024))

    archivo.stream.seek(0)
    contenido = archivo.stream.read(max_bytes + 1)
    archivo.stream.seek(0)

    tamano = len(contenido)
    if tamano <= 0:
        raise ValueError('El archivo está vacío.')
    if tamano > max_bytes:
        max_mb = round(max_bytes / (1024 * 1024), 1)
        raise ValueError(f'El archivo supera el límite permitido de {max_mb} MB.')

    if not firma_binaria_valida(contenido[:16], extension):
        raise ValueError('El contenido real del archivo no coincide con el formato declarado.')

    sha256 = hashlib.sha256(contenido).hexdigest()
    nombre_interno = f'{secrets.token_hex(24)}.{extension}'
    ruta_relativa = f'{subcarpeta}/{nombre_interno}'

    carpeta_destino = os.path.join(obtener_raiz_privada(), subcarpeta)
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_absoluta = resolver_ruta_privada(ruta_relativa)
    if not ruta_absoluta:
        raise ValueError('Ruta de destino inválida.')

    with open(ruta_absoluta, 'wb') as f:
        f.write(contenido)

    return ResultadoAlmacenamiento(
        nombre_original=nombre_seguro[:255],
        nombre_interno=nombre_interno,
        ruta_relativa=ruta_relativa,
        extension=extension,
        mime_type=MIME_POR_EXTENSION[extension],
        tamano_bytes=tamano,
        sha256=sha256,
    )


def eliminar_documento_privado(ruta_relativa):
    """Elimina físicamente un archivo privado si existe dentro de la raíz segura."""
    ruta_abs = resolver_ruta_privada(ruta_relativa)
    if ruta_abs and os.path.isfile(ruta_abs):
        os.remove(ruta_abs)
        return True
    return False
