"""
BioAula — Suite de Pruebas Automatizadas
Ejecutable directamente con: python run_tests.py
No requiere pytest instalado en el entorno.
"""

import sys
import os
import unittest
import json

# Asegurar path de búsqueda
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from backend import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.quiz import Quiz, QuizQuestion, QuizAttempt
from backend.reports.analytics_service import get_quiz_report_data
from backend.reports.pdf_generator import generate_report


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key-32chars-for-testing'
    JWT_SECRET_KEY = 'test-jwt-secret-key-32chars-testing'
    JWT_ACCESS_TOKEN_EXPIRES = 3600


class BioAulaTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_01_registro_estudiante_exitoso(self):
        """Valida que un estudiante pueda registrarse normalmente."""
        res = self.client.post('/api/auth/register', json={
            'nombre': 'Estudiante Test',
            'correo': 'estudiante@bioaula.edu.co',
            'password': 'password123',
            'rol': 'estudiante',
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn('token', data)
        self.assertEqual(data['user']['rol'], 'estudiante')

    def test_02_bloqueo_escalacion_admin(self):
        """Seguridad: Verifica que la API pública rechace el rol admin."""
        res = self.client.post('/api/auth/register', json={
            'nombre': 'Hacker Admin',
            'correo': 'hacker@bioaula.edu.co',
            'password': 'password123',
            'rol': 'admin',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('error', res.get_json())

    def test_03_validacion_contrasena_minima(self):
        """Valida la regla de seguridad de mínimo 8 caracteres."""
        res = self.client.post('/api/auth/register', json={
            'nombre': 'Test Corto',
            'correo': 'corto@bioaula.edu.co',
            'password': '12345',
            'rol': 'estudiante',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('8 caracteres', res.get_json()['error'])

    def test_04_seguridad_endpoint_publico_quiz(self):
        """Anti-Fraude: El endpoint público NO debe filtrar respuestas correctas ni explicaciones."""
        # 1. Crear profesor y obtener token
        reg = self.client.post('/api/auth/register', json={
            'nombre': 'Profesor Biología',
            'correo': 'profe@bioaula.edu.co',
            'password': 'profepassword123',
            'rol': 'profesor',
        })
        token = reg.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}

        # 2. Crear examen con respuestas
        quiz_res = self.client.post('/api/quizzes', json={
            'titulo': 'Genética y Mendel',
            'nivel': 'bachillerato',
            'numQ': 2,
            'bankSize': 2,
            'apoyo': 'Resumen sobre genética mendeliana.',
            'banco': [
                {
                    'pregunta': '¿Qué es un fenotipo?',
                    'opciones': ['Expresión física observable', 'Composición genética interna', 'Un cromosoma', 'Un aminoácido'],
                    'correcta': 0,
                    'explicacion': 'El fenotipo es la manifestación física observable del genotipo.',
                    'subtema': 'Genética básica',
                }
            ]
        }, headers=headers)
        self.assertEqual(quiz_res.status_code, 201)
        quiz_id = quiz_res.get_json()['quiz']['id']

        # 3. Consultar como estudiante en la API pública
        pub_res = self.client.get(f'/api/public/quizzes/{quiz_id}')
        self.assertEqual(pub_res.status_code, 200)
        pub_data = pub_res.get_json()

        for q in pub_data['banco']:
            self.assertNotIn('correcta', q, "¡Alerta de fraude! 'correcta' visible para estudiantes.")
            self.assertNotIn('explicacion', q, "¡Alerta! 'explicacion' filtrada antes de resolver la prueba.")

    def test_05_calificacion_en_servidor_evita_fraude(self):
        """Seguridad: El servidor evalúa las respuestas contra la BD y no confía en el cliente."""
        reg = self.client.post('/api/auth/register', json={
            'nombre': 'Profesor Quizzes',
            'correo': 'profe2@bioaula.edu.co',
            'password': 'password123',
            'rol': 'profesor',
        })
        headers = {'Authorization': f"Bearer {reg.get_json()['token']}"}

        quiz_res = self.client.post('/api/quizzes', json={
            'titulo': 'Fotosíntesis',
            'banco': [
                {
                    'pregunta': '¿Qué gas absorben las plantas durante la fase luminosa/oscura?',
                    'opciones': ['Oxígeno', 'Dióxido de carbono', 'Nitrógeno', 'Metano'],
                    'correcta': 1, # CO2
                    'explicacion': 'Las plantas fijan CO2.',
                    'subtema': 'Fotosíntesis',
                }
            ]
        }, headers=headers)
        quiz_id = quiz_res.get_json()['quiz']['id']

        # Estudiante intenta mandar selected=0 (Oxígeno, incorrecto) pero mintiendo con correct=0
        cheat_payload = {
            'nombre': 'Estudiante Sospechoso',
            'documento': '1098765432',
            'respuestas': [
                {
                    'pregunta': '¿Qué gas absorben las plantas durante la fase luminosa/oscura?',
                    'selected': 0,
                    'correct': 0, # Falso
                }
            ]
        }
        sub_res = self.client.post(f'/api/quizzes/{quiz_id}/submit', json=cheat_payload)
        self.assertEqual(sub_res.status_code, 201)
        res_data = sub_res.get_json()

        # El servidor debe calificar con 0 y marcar is_correct: False
        self.assertEqual(res_data['attempt']['puntaje'], 0)
        self.assertEqual(res_data['attempt']['porcentaje'], 0)
        self.assertFalse(res_data['evaluated'][0]['is_correct'])
        self.assertEqual(res_data['evaluated'][0]['correct'], 1)

    def test_06_generacion_reporte_pdf(self):
        """Valida que ReportLab genere el PDF correctamente en memoria."""
        prof = User(nombre='Docente PDF', correo='docente_pdf@bioaula.com', rol='profesor')
        prof.set_password('pass123456')
        db.session.add(prof)
        db.session.commit()

        quiz = Quiz(
            titulo='Evaluación de Prueba',
            profesor_id=prof.id,
            json_original='{}',
            nivel='secundaria',
            num_q=1,
            bank_size=1,
        )
        db.session.add(quiz)
        db.session.commit()

        report_data = get_quiz_report_data(quiz)
        pdf_buffer = generate_report(report_data)
        self.assertTrue(pdf_buffer.getvalue().startswith(b'%PDF-'))


if __name__ == '__main__':
    print("=" * 60)
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS DE BIOAULA")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(BioAulaTestCase)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE.")
        sys.exit(0)
    else:
        print("\n❌ ERRORES DETECTADOS EN LAS PRUEBAS.")
        sys.exit(1)
