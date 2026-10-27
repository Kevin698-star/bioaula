import json
from datetime import datetime, timezone
from flask import jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import quizzes_bp
from ..models.quiz import Quiz, QuizQuestion, QuizAttempt
from ..models.user import User
from ..extensions import db
from .services import validate_quiz_data, validate_submit_data


@quizzes_bp.route('', methods=['POST'])
@jwt_required()
def create_quiz():
    user_id = get_jwt_identity()
    profesor = db.session.get(User, int(user_id)) if user_id else None
    if not profesor or profesor.rol not in ('admin', 'profesor'):
        return jsonify({'error': 'Solo profesores y administradores pueden crear pruebas'}), 403

    data = request.get_json()
    error = validate_quiz_data(data)
    if error:
        return jsonify({'error': error}), 400

    titulo = data.get('titulo') or data.get('topic', 'Sin título')
    nivel = data.get('nivel')
    num_q = data.get('numQ')
    bank_size = data.get('bankSize')
    apoyo = data.get('apoyo')

    json_original = json.dumps(data, ensure_ascii=False)

    quiz = Quiz(
        titulo=titulo,
        profesor_id=profesor.id,
        json_original=json_original,
        nivel=nivel,
        num_q=num_q,
        bank_size=bank_size,
        apoyo=apoyo,
    )
    db.session.add(quiz)
    db.session.flush()

    for q_data in data['banco']:
        question = QuizQuestion(
            quiz_id=quiz.id,
            pregunta=q_data['pregunta'],
            opciones=json.dumps(q_data['opciones'], ensure_ascii=False),
            respuesta_correcta=q_data['correcta'],
            explicacion=q_data.get('explicacion', ''),
            subtema=q_data.get('subtema', ''),
        )
        db.session.add(question)

    db.session.commit()

    return jsonify({'quiz': quiz.to_dict(include_questions=True)}), 201


@quizzes_bp.route('', methods=['GET'])
@jwt_required()
def list_quizzes():
    user_id = get_jwt_identity()
    profesor = db.session.get(User, int(user_id)) if user_id else None
    if not profesor:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    if profesor.rol == 'admin':
        quizzes = Quiz.query.order_by(Quiz.fecha_creacion.desc()).all()
    else:
        quizzes = Quiz.query.filter_by(profesor_id=profesor.id)\
            .order_by(Quiz.fecha_creacion.desc()).all()

    return jsonify({'quizzes': [q.to_dict() for q in quizzes]})


@quizzes_bp.route('/<int:quiz_id>', methods=['GET'])
@jwt_required()
def get_quiz(quiz_id):
    user_id = get_jwt_identity()
    profesor = db.session.get(User, int(user_id)) if user_id else None
    if not profesor:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return jsonify({'error': 'Prueba no encontrada'}), 404

    if profesor.rol != 'admin' and quiz.profesor_id != profesor.id:
        return jsonify({'error': 'No tienes acceso a esta prueba'}), 403

    return jsonify({'quiz': quiz.to_dict(include_questions=True)})


@quizzes_bp.route('/<int:quiz_id>/submit', methods=['POST'])
def submit_attempt(quiz_id):
    """
    Recibe las respuestas del estudiante, las califica DE FORMA SEGURA contra
    la base de datos (evitando fraude en el cliente) y deduplica por documento.
    """
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return jsonify({'error': 'Prueba no encontrada'}), 404

    data = request.get_json()
    error = validate_submit_data(data)
    if error:
        return jsonify({'error': error}), 400

    respuestas_client = data['respuestas']
    doc_clean = data['documento'].strip()
    nombre_clean = data['nombre'].strip()

    # Mapear preguntas reales de la base de datos para verificación confiable
    db_questions_by_id = {q.id: q for q in quiz.questions}
    db_questions_by_text = {q.pregunta.strip(): q for q in quiz.questions}

    evaluated_respuestas = []
    score = 0

    for item in respuestas_client:
        selected_option = item.get('selected')

        # Buscar la pregunta real en el banco de la base de datos
        q_obj = None
        if item.get('question_id') in db_questions_by_id:
            q_obj = db_questions_by_id[item['question_id']]
        elif item.get('id') in db_questions_by_id:
            q_obj = db_questions_by_id[item['id']]
        elif item.get('pregunta', '').strip() in db_questions_by_text:
            q_obj = db_questions_by_text[item['pregunta'].strip()]

        if q_obj:
            correct_index = q_obj.respuesta_correcta
            pregunta_text = q_obj.pregunta
            subtema_text = q_obj.subtema or ''
            explicacion_text = q_obj.explicacion or ''
            opciones_list = json.loads(q_obj.opciones) if q_obj.opciones else []
            qid = q_obj.id
        else:
            # Fallback seguro
            correct_index = item.get('correct')
            pregunta_text = item.get('pregunta', '')
            subtema_text = item.get('subtema', '')
            explicacion_text = item.get('explicacion', '')
            opciones_list = item.get('opciones', [])
            qid = item.get('question_id') or item.get('id')

        is_correct = (selected_option is not None and selected_option == correct_index)
        if is_correct:
            score += 1

        evaluated_respuestas.append({
            'question_id': qid,
            'pregunta': pregunta_text,
            'opciones': opciones_list,
            'selected': selected_option,
            'correct': correct_index,
            'is_correct': is_correct,
            'subtema': subtema_text,
            'explicacion': explicacion_text,
        })

    total = len(evaluated_respuestas)
    pct = round((score / total) * 100) if total > 0 else 0

    # Deduplicación por documento de estudiante
    existing_attempt = QuizAttempt.query.filter_by(
        quiz_id=quiz.id,
        documento_estudiante=doc_clean
    ).first()

    if existing_attempt:
        existing_attempt.nombre_estudiante = nombre_clean
        existing_attempt.puntaje = score
        existing_attempt.total_preguntas = total
        existing_attempt.porcentaje = pct
        existing_attempt.respuestas = json.dumps(evaluated_respuestas, ensure_ascii=False)
        existing_attempt.fecha = datetime.now(timezone.utc)
        attempt = existing_attempt
    else:
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            nombre_estudiante=nombre_clean,
            documento_estudiante=doc_clean,
            puntaje=score,
            total_preguntas=total,
            porcentaje=pct,
            respuestas=json.dumps(evaluated_respuestas, ensure_ascii=False),
        )
        db.session.add(attempt)

    db.session.commit()

    return jsonify({
        'attempt': attempt.to_dict(),
        'evaluated': evaluated_respuestas,
    }), 201


@quizzes_bp.route('/<int:quiz_id>/attempts', methods=['GET'])
@jwt_required()
def list_attempts(quiz_id):
    user_id = get_jwt_identity()
    profesor = db.session.get(User, int(user_id)) if user_id else None
    if not profesor:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return jsonify({'error': 'Prueba no encontrada'}), 404

    if profesor.rol != 'admin' and quiz.profesor_id != profesor.id:
        return jsonify({'error': 'No tienes acceso a esta prueba'}), 403

    return jsonify({'attempts': [a.to_dict() for a in quiz.attempts]})


@quizzes_bp.route('/<int:quiz_id>/report', methods=['GET'])
@jwt_required()
def download_report(quiz_id):
    user_id = get_jwt_identity()
    profesor = db.session.get(User, int(user_id)) if user_id else None
    if not profesor:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return jsonify({'error': 'Prueba no encontrada'}), 404

    if profesor.rol != 'admin' and quiz.profesor_id != profesor.id:
        return jsonify({'error': 'No tienes acceso a esta prueba'}), 403

    from ..reports.analytics_service import get_quiz_report_data
    from ..reports.pdf_generator import generate_report

    report_data = get_quiz_report_data(quiz)
    pdf_buffer = generate_report(report_data)

    safe_title = quiz.titulo.replace('/', '_').replace('\\', '_').replace(' ', '_')[:50]
    today = datetime.now().strftime('%Y%m%d')
    filename = f'Informe_{safe_title}_{today}.pdf'

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )
