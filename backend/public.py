from flask import Blueprint, jsonify
from .models.quiz import Quiz
from .extensions import db

public_bp = Blueprint('public', __name__)


@public_bp.route('/api/public/quizzes/<int:quiz_id>')
def get_public_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return jsonify({'error': 'Prueba no encontrada'}), 404

    # Retorna las preguntas de forma segura usando to_public_dict (sin 'correcta' ni 'explicacion')
    return jsonify(quiz.to_public_dict())
