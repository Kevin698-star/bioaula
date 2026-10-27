from flask import Blueprint

quizzes_bp = Blueprint('quizzes', __name__)

from . import routes
