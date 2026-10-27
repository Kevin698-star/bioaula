import os
import sys

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from dotenv import load_dotenv

# Cargar variables de entorno desde .env de forma robusta
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bioaula-secret-key-change-in-production-32chars')

    # Resolver SQLite de forma absoluta y normalizada con barras inclinadas hacia adelante (evita errores en Windows)
    _raw_db = os.environ.get('DATABASE_URL')
    if not _raw_db or _raw_db == 'sqlite:///bioaula.db':
        _db_path = os.path.join(basedir, 'bioaula.db').replace('\\', '/')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{_db_path}'
    else:
        SQLALCHEMY_DATABASE_URI = _raw_db.replace('\\', '/')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'bioaula-jwt-secret-change-in-production-32')
    JWT_ACCESS_TOKEN_EXPIRES = 86400
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
