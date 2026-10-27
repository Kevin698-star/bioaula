import json
from datetime import datetime, timezone
from ..extensions import db


class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    profesor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    json_original = db.Column(db.Text, nullable=False)
    nivel = db.Column(db.String(50), nullable=True)
    num_q = db.Column(db.Integer, nullable=True)
    bank_size = db.Column(db.Integer, nullable=True)
    apoyo = db.Column(db.Text, nullable=True)

    questions = db.relationship(
        'QuizQuestion', backref='quiz', lazy='selectin',
        cascade='all, delete-orphan', order_by='QuizQuestion.id'
    )
    attempts = db.relationship(
        'QuizAttempt', backref='quiz', lazy='selectin',
        cascade='all, delete-orphan', order_by='QuizAttempt.fecha'
    )

    def to_dict(self, include_questions=False):
        d = {
            'id': self.id,
            'titulo': self.titulo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'profesor_id': self.profesor_id,
            'nivel': self.nivel,
            'num_q': self.num_q,
            'bank_size': self.bank_size,
        }
        if include_questions:
            d['banco'] = [q.to_dict() for q in self.questions]
            d['apoyo'] = self.apoyo
            d['json_original'] = self.json_original
            d['attempts'] = [a.to_dict() for a in self.attempts]
        return d

    def to_public_dict(self):
        """Retorna el examen público SIN exponer respuestas correctas ni explicaciones previas."""
        return {
            'id': self.id,
            'titulo': self.titulo,
            'nivel': self.nivel,
            'num_q': self.num_q,
            'bank_size': self.bank_size,
            'banco': [q.to_public_dict() for q in self.questions],
            'apoyo': self.apoyo,
        }


class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    pregunta = db.Column(db.Text, nullable=False)
    opciones = db.Column(db.Text, nullable=False)
    respuesta_correcta = db.Column(db.Integer, nullable=False)
    explicacion = db.Column(db.Text, nullable=True)
    subtema = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        """Incluye la respuesta correcta y explicación (uso exclusivo profesor/backend)."""
        return {
            'id': self.id,
            'pregunta': self.pregunta,
            'opciones': json.loads(self.opciones) if self.opciones else [],
            'correcta': self.respuesta_correcta,
            'explicacion': self.explicacion,
            'subtema': self.subtema,
        }

    def to_public_dict(self):
        """Oculta deliberadamente la respuesta correcta para evitar filtraciones en el cliente."""
        return {
            'id': self.id,
            'pregunta': self.pregunta,
            'opciones': json.loads(self.opciones) if self.opciones else [],
            'subtema': self.subtema,
        }


class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    nombre_estudiante = db.Column(db.String(100), nullable=False)
    documento_estudiante = db.Column(db.String(50), nullable=False)
    puntaje = db.Column(db.Integer, nullable=False)
    total_preguntas = db.Column(db.Integer, nullable=False)
    porcentaje = db.Column(db.Integer, nullable=False)
    respuestas = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self, include_details=True):
        d = {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'nombre': self.nombre_estudiante,
            'documento': self.documento_estudiante,
            'puntaje': self.puntaje,
            'total': self.total_preguntas,
            'porcentaje': self.porcentaje,
            'fecha': self.fecha.isoformat() if self.fecha else None,
        }
        if include_details and self.respuestas:
            try:
                resp_list = json.loads(self.respuestas)
                d['respuestas'] = resp_list
                subtemas = {}
                for r in resp_list:
                    sub = r.get('subtema') or 'General'
                    if sub not in subtemas:
                        subtemas[sub] = {'ok': 0, 'total': 0}
                    subtemas[sub]['total'] += 1
                    if r.get('selected') == r.get('correct'):
                        subtemas[sub]['ok'] += 1
                d['subtemas'] = subtemas
            except Exception:
                d['respuestas'] = []
                d['subtemas'] = {}
        else:
            d['respuestas'] = []
            d['subtemas'] = {}
        return d
