import pytest
import os
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app
from backend.extensions import db
from backend.models.user import User


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = 3600


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def teacher_auth(client):
    # Crear profesor
    res = client.post('/api/auth/register', json={
        'nombre': 'Profesor Biología',
        'correo': 'profesor@bioaula.edu.co',
        'password': 'password123',
        'rol': 'profesor',
    })
    token = res.get_json()['token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_auth(app, client):
    # Crear admin directamente en BD (ya que no se permite registro público)
    with app.app_context():
        admin = User(nombre='Admin BioAula', correo='admin@bioaula.edu.co', rol='admin')
        admin.set_password('adminpassword123')
        db.session.add(admin)
        db.session.commit()

    res = client.post('/api/auth/login', json={
        'correo': 'admin@bioaula.edu.co',
        'password': 'adminpassword123',
    })
    token = res.get_json()['token']
    return {'Authorization': f'Bearer {token}'}
