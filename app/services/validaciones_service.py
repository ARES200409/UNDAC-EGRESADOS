"""Validaciones y sanitización reutilizables para formularios y rutas."""

from datetime import date
import re


def limpiar_texto(valor, max_len=None):
    """Recorta espacios y aplica longitud máxima opcional."""
    texto = str(valor or '').strip()
    if max_len is not None and max_len > 0:
        texto = texto[:max_len]
    return texto


def parse_fecha_iso(valor, obligatoria=False):
    """Convierte 'YYYY-MM-DD' a datetime.date o devuelve None si es opcional y vacía.

    Lanza ValueError si es obligatoria y falta, o si el formato es inválido.
    """
    texto = str(valor or '').strip()
    if not texto:
        if obligatoria:
            raise ValueError('La fecha es obligatoria.')
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError as exc:
        raise ValueError('Formato de fecha inválido (usa AAAA-MM-DD).') from exc


def entero_en_rango(valor, minimo, maximo, obligatorio=False):
    """Convierte a int validando rango; devuelve None si es opcional y vacío."""
    texto = str(valor or '').strip()
    if not texto:
        if obligatorio:
            raise ValueError('Este valor numérico es obligatorio.')
        return None
    try:
        numero = int(texto)
    except ValueError as exc:
        raise ValueError('Debe ingresar un número entero válido.') from exc
    if numero < minimo or numero > maximo:
        raise ValueError(f'El valor debe estar entre {minimo} y {maximo}.')
    return numero


def validar_ruc_peru(ruc):
    """Valida formato básico de RUC peruano (11 dígitos numéricos, prefijos válidos)."""
    texto = str(ruc or '').strip()
    if not re.fullmatch(r'(10|15|17|20)\d{9}', texto):
        return False
    return True
