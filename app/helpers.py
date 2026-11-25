# app/helpers.py
"""Funciones auxiliares de NEXO UNDAC.

Mantiene las interfaces que ya usan las rutas de Flask:
- consultar_api(codigo_universitario)
- datos_api_a_egresado(datos)
- resolver_curricula(codigo_curricula, anio_ingreso, nombre_programa, id_escuela)
- extension_permitida(nombre_archivo, extensiones)
- guardar_archivo(archivo, subcarpeta)
"""

import os
import re
import secrets
import unicodedata
from urllib.parse import quote

import requests
from flask import current_app
from werkzeug.utils import secure_filename


# ------------------------------------------------------------
# API UNIVERSITARIA
# ------------------------------------------------------------
# Conserva el endpoint actual para no interrumpir el proyecto.
# Para un despliegue institucional, trasladarlo a UNDAC_API_BASE en .env.
API_BASE = os.getenv(
    "UNDAC_API_BASE",
    "https://api.undac.edu.pe/tasks/a3945a7384cbdcd33f49e8f5b8ec29f5/91f33e2776c526b9cca723a63476f028",
).rstrip("/")


def consultar_api(codigo_universitario):
    """Consulta un registro académico de la API.

    Devuelve un diccionario si la respuesta HTTP es correcta y JSON
    tiene formato de objeto. Devuelve None en caso contrario.
    La condición de egresado y la identidad se validan en las rutas.
    """
    codigo = str(codigo_universitario or "").strip()
    if not codigo:
        return None

    try:
        respuesta = requests.get(
            f"{API_BASE}/{quote(codigo, safe='')}",
            timeout=(5, 10),
            headers={"Accept": "application/json"},
        )
        if respuesta.status_code != 200:
            return None

        datos = respuesta.json()
        return datos if isinstance(datos, dict) else None
    except (requests.exceptions.RequestException, ValueError):
        return None


def datos_api_a_egresado(datos):
    """Traduce campos de la API a los nombres del modelo Egresados."""
    datos = datos if isinstance(datos, dict) else {}
    return {
        "apellido_paterno": datos.get("Apellido paterno", ""),
        "apellido_materno": datos.get("Apellido materno", ""),
        "nombres": datos.get("Nombres", ""),
        "correo_institucional": datos.get("Correo Institucional", ""),
        "dni": datos.get("Dni", ""),
        "fecha_nacimiento": datos.get("Fecha de nacimiento"),
        "anio_ingreso": datos.get("Fecha de Ingreso"),
        "domicilio": datos.get("Domicilio", ""),
        "genero": datos.get("Genero", ""),
    }


def _normalizar_texto(valor):
    """Compara nombres/códigos ignorando espacios y mayúsculas."""
    texto = unicodedata.normalize("NFKC", str(valor or ""))
    return " ".join(texto.casefold().split())


def resolver_curricula(codigo_curricula, anio_ingreso,
                      nombre_programa=None, id_escuela=None):
    """Busca una currícula oficial ya registrada en MySQL.

    Prioridad: código exacto de escuela y luego nombre exacto del
    programa. No deduce programas a partir de sufijos: pueden ser
    ambiguos. Tampoco crea currículas con el año de ingreso de una
    persona, porque ese año no necesariamente es el inicio del plan.

    'anio_ingreso' se conserva para compatibilidad con auth/routes.py.
    Si no hay una correspondencia única registrada, devuelve None.
    """
    from app.models import Curriculas, ProgramasEstudio

    codigo = str(codigo_curricula or "").strip()
    escuela = _normalizar_texto(id_escuela)
    nombre = _normalizar_texto(nombre_programa)
    if not codigo:
        return None

    programas = ProgramasEstudio.query.filter_by(estado="activo").all()
    programa = None

    if escuela:
        coincidencias = [
            p for p in programas
            if p.codigo is not None and _normalizar_texto(p.codigo) == escuela
        ]
        if len(coincidencias) == 1:
            programa = coincidencias[0]
        elif len(coincidencias) > 1:
            return None

    if programa is None and nombre:
        coincidencias = [
            p for p in programas
            if _normalizar_texto(p.nombre) == nombre
        ]
        if len(coincidencias) == 1:
            programa = coincidencias[0]
        elif len(coincidencias) > 1:
            return None

    if programa is None:
        return None

    return Curriculas.query.filter_by(
        id_programa=programa.id_programa,
        nombre=codigo,
        estado="activo",
    ).first()


# ------------------------------------------------------------
# MANEJO DE ARCHIVOS (compatible con las rutas actuales)
# ------------------------------------------------------------
EXTENSIONES_IMAGEN = {"png", "jpg", "jpeg", "webp"}
EXTENSIONES_DOCUMENTO = {"pdf", "jpg", "jpeg", "png"}
SUBCARPETAS_IMAGEN = {"fotos", "ofertas", "portada", "noticias", "empresas", "perfiles"}


def extension_permitida(nombre_archivo, extensiones):
    """Comprueba la extensión indicada, no valida por sí sola el contenido."""
    nombre = secure_filename(str(nombre_archivo or ""))
    return (
        "." in nombre
        and nombre.rsplit(".", 1)[1].lower() in extensiones
    )


def _firma_compatible(archivo, extension):
    """Comprueba cabeceras de tipos admitidos; no sustituye un antivirus."""
    archivo.stream.seek(0)
    firma = archivo.stream.read(16)
    archivo.stream.seek(0)

    if extension == "pdf":
        return firma.startswith(b"%PDF-")
    if extension == "png":
        return firma.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in ("jpg", "jpeg"):
        return firma.startswith(b"\xff\xd8\xff")
    if extension == "webp":
        return firma.startswith(b"RIFF") and firma[8:12] == b"WEBP"
    return False


def guardar_archivo(archivo, subcarpeta):
    """Guarda un archivo y devuelve la ruta relativa usada por Flask.

    Mantiene 'uploads/<subcarpeta>/<nombre>' para no romper las rutas
    actuales. Evita sobrescribir archivos homónimos con nombres aleatorios.

    ADVERTENCIA: 'static/uploads' es público. No utilizar esta función
    para documentos privados de producción sin migrar las rutas de
    lectura/descarga a un almacenamiento protegido por autorización.
    """
    if not archivo or not archivo.filename:
        return None

    subcarpeta = str(subcarpeta or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", subcarpeta):
        return None

    extensiones = (
        EXTENSIONES_IMAGEN
        if subcarpeta in SUBCARPETAS_IMAGEN
        else EXTENSIONES_DOCUMENTO
    )
    nombre = secure_filename(archivo.filename)
    if not extension_permitida(nombre, extensiones):
        return None

    extension = nombre.rsplit(".", 1)[1].lower()
    limite = 10 * 1024 * 1024 if subcarpeta in SUBCARPETAS_IMAGEN else 20 * 1024 * 1024

    try:
        archivo.stream.seek(0, os.SEEK_END)
        tamano = archivo.stream.tell()
        archivo.stream.seek(0)

        if tamano <= 0 or tamano > limite:
            return None
        if not _firma_compatible(archivo, extension):
            return None

        nombre_unico = f"{secrets.token_hex(16)}.{extension}"
        carpeta = os.path.join(current_app.static_folder, "uploads", subcarpeta)
        os.makedirs(carpeta, exist_ok=True)
        ruta_disco = os.path.join(carpeta, nombre_unico)
        archivo.save(ruta_disco)
        return f"uploads/{subcarpeta}/{nombre_unico}"
    except (OSError, ValueError):
        return None
