"""Configuración de Gunicorn para el servicio web de Render."""

import os


bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
