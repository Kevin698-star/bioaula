from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from ..models.user import User
from ..extensions import db


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = db.session.get(User, int(user_id)) if user_id else None
        if not user or user.rol != 'admin':
            return jsonify({'error': 'Acceso denegado: se requiere rol administrador'}), 403
        return fn(*args, **kwargs)
    return wrapper


def teacher_or_admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = db.session.get(User, int(user_id)) if user_id else None
        if not user or user.rol not in ('admin', 'profesor'):
            return jsonify({'error': 'Acceso denegado: se requiere rol profesor o administrador'}), 403
        return fn(*args, **kwargs)
    return wrapper
