import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv('SECRET_KEY')
    SOLO_SISTEMAS = os.getenv('NEXO_SOLO_SISTEMAS', 'true').lower() == 'true'
    SQLALCHEMY_DATABASE_URI = URL.create(
        'mysql+pymysql',
        username=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3306')),
        database=os.getenv('DB_NAME', 'seguimiento_egresados')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # En producción HTTPS, definir SESSION_COOKIE_SECURE=true en .env.
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    PREFERRED_URL_SCHEME = 'https' if SESSION_COOKIE_SECURE else 'http'

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB máximo por petición HTTP
    MAX_DOCUMENT_BYTES = int(os.getenv('MAX_DOCUMENT_BYTES', 10 * 1024 * 1024))
    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    PRIVATE_STORAGE_DIR = os.getenv(
        'PRIVATE_STORAGE_DIR',
        os.path.join(BASE_DIR, 'instance', 'storage_privado')
    )
    LOGIN_MAX_ATTEMPTS = int(os.getenv('LOGIN_MAX_ATTEMPTS', '5'))
    LOGIN_LOCKOUT_SECONDS = int(os.getenv('LOGIN_LOCKOUT_SECONDS', '300'))

    # Configuración del correo electrónico
    MAIL_SERVER         = os.getenv('MAIL_SERVER')
    MAIL_PORT           = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS        = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME       = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD       = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    # -----------------------------------------------------------
    # Integración con fuentes oficiales (módulo DNI)
    # -----------------------------------------------------------
    RENIEC_API_URL  = os.getenv('RENIEC_API_URL', '')
    RENIEC_API_KEY  = os.getenv('RENIEC_API_KEY', '')
    SUNEDU_API_URL  = os.getenv('SUNEDU_API_URL', '')
    SUNEDU_API_KEY  = os.getenv('SUNEDU_API_KEY', '')
    SUNEDU_DATASET_CSV = os.getenv('SUNEDU_DATASET_CSV', '')  # ruta al CSV de datos.gob.pe
    DNI_LOOKUP_RATE_LIMIT = int(os.getenv('DNI_LOOKUP_RATE_LIMIT', '10'))  # consultas/hora/IP