"""Punto WSGI para Waitress (Windows) u otro servidor compatible."""
from app import create_app

app = create_app()
