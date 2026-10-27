from backend.models.quiz import Quiz, QuizQuestion, QuizAttempt
from backend.models.user import User
from backend.extensions import db
from backend.reports.analytics_service import get_quiz_report_data
from backend.reports.pdf_generator import generate_report


def test_pdf_report_generation(app):
    with app.app_context():
        prof = User(nombre='Profe Carlos', correo='carlos@bioaula.com', rol='profesor')
        prof.set_password('pass123456')
        db.session.add(prof)
        db.session.commit()

        quiz = Quiz(
            titulo='Evaluación Ecosistemas',
            profesor_id=prof.id,
            json_original='{}',
            nivel='bachillerato',
            num_q=1,
            bank_size=1,
        )
        db.session.add(quiz)
        db.session.commit()

        # Agregar intento
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            nombre_estudiante='Ana Pérez',
            documento_estudiante='10001',
            puntaje=1,
            total_preguntas=1,
            porcentaje=100,
            respuestas='[{"pregunta": "Pregunta 1", "selected": 0, "correct": 0, "subtema": "Biomas"}]',
        )
        db.session.add(attempt)
        db.session.commit()

        report_data = get_quiz_report_data(quiz)
        assert report_data['total_attempts'] == 1
        assert report_data['avg'] == 100
        assert report_data['aprobados'] == 1

        pdf_buf = generate_report(report_data)
        pdf_bytes = pdf_buf.getvalue()

        # Validar que sea un PDF válido (comienza con %PDF-)
        assert pdf_bytes.startswith(b'%PDF-')
        assert len(pdf_bytes) > 1000
