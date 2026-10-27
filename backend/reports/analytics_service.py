import json
from ..models.quiz import QuizAttempt
from ..models.user import User
from ..extensions import db


def get_quiz_report_data(quiz):
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).all()
    profesor = db.session.get(User, quiz.profesor_id) if quiz.profesor_id else None

    # Deduplicación por documento de identidad (conservando la mejor calificación)
    unique_attempts = {}
    for a in attempts:
        doc = a.documento_estudiante or str(a.id)
        if doc not in unique_attempts or a.porcentaje > unique_attempts[doc].porcentaje:
            unique_attempts[doc] = a

    deduped = list(unique_attempts.values())
    total_attempts = len(deduped)
    scores = [a.porcentaje for a in deduped]

    avg = round(sum(scores) / total_attempts) if total_attempts > 0 else 0
    max_score = max(scores) if total_attempts > 0 else 0
    min_score = min(scores) if total_attempts > 0 else 0
    aprobados = sum(1 for s in scores if s >= 60)
    pct_aprobacion = round((aprobados / total_attempts) * 100) if total_attempts > 0 else 0

    students = sorted(deduped, key=lambda a: a.porcentaje, reverse=True)

    errors_by_q = {}
    for a in deduped:
        if not a.respuestas:
            continue
        try:
            respuestas = json.loads(a.respuestas)
            for r in respuestas:
                qtext = r.get('pregunta', '').strip()
                if not qtext:
                    continue
                if qtext not in errors_by_q:
                    errors_by_q[qtext] = {
                        'pregunta': qtext,
                        'subtema': r.get('subtema', 'General'),
                        'total': 0,
                        'errores': 0,
                    }
                errors_by_q[qtext]['total'] += 1
                if r.get('selected') != r.get('correct'):
                    errors_by_q[qtext]['errores'] += 1
        except Exception:
            pass

    most_failed = sorted(errors_by_q.values(), key=lambda x: x['errores'], reverse=True)[:10]
    for item in most_failed:
        item['pct_error'] = round((item['errores'] / item['total']) * 100) if item['total'] > 0 else 0

    return {
        'quiz': quiz,
        'profesor': profesor,
        'total_attempts': total_attempts,
        'avg': avg,
        'max_score': max_score,
        'min_score': min_score,
        'aprobados': aprobados,
        'pct_aprobacion': pct_aprobacion,
        'students': students,
        'most_failed': most_failed,
    }
