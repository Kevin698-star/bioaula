from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity
from . import admin_bp
from ..auth.decorators import admin_required
from ..models.user import User
from ..models.quiz import Quiz, QuizAttempt
from ..extensions import db
from .services import validate_user_data


@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    total_usuarios = User.query.count()
    total_profesores = User.query.filter_by(rol='profesor').count()
    total_estudiantes = User.query.filter_by(rol='estudiante').count()
    total_pruebas = Quiz.query.count()
    total_intentos = QuizAttempt.query.count()

    return jsonify({
        'total_usuarios': total_usuarios,
        'total_profesores': total_profesores,
        'total_estudiantes': total_estudiantes,
        'total_pruebas': total_pruebas,
        'total_intentos': total_intentos,
    })


@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    search = request.args.get('search', '').strip()
    rol = request.args.get('rol', '').strip()

    query = User.query
    if search:
        query = query.filter(
            (User.nombre.ilike(f'%{search}%')) | (User.correo.ilike(f'%{search}%'))
        )
    if rol and rol in ('admin', 'profesor', 'estudiante'):
        query = query.filter_by(rol=rol)

    users = query.order_by(User.creado.desc()).all()
    return jsonify({
        'users': [{
            'id': u.id,
            'nombre': u.nombre,
            'correo': u.correo,
            'rol': u.rol,
            'fecha_creacion': u.creado.isoformat() if u.creado else None,
        } for u in users]
    })


@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    error = validate_user_data(data)
    if error:
        return jsonify({'error': error}), 400

    correo_clean = data['correo'].strip().lower()
    if User.query.filter_by(correo=correo_clean).first():
        return jsonify({'error': 'El correo ya está registrado'}), 409

    user = User(
        nombre=data['nombre'].strip(),
        correo=correo_clean,
        rol=data['rol'],
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({'user': user.to_dict()}), 201


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    data = request.get_json()
    error = validate_user_data(data, is_update=True)
    if error:
        return jsonify({'error': error}), 400

    if 'nombre' in data and data['nombre'].strip():
        user.nombre = data['nombre'].strip()
    if 'correo' in data and data['correo'].strip():
        new_correo = data['correo'].strip().lower()
        existing = User.query.filter(User.correo == new_correo, User.id != user_id).first()
        if existing:
            return jsonify({'error': 'El correo ya está registrado por otro usuario'}), 409
        user.correo = new_correo
    if 'rol' in data and data['rol'] in ('admin', 'profesor', 'estudiante'):
        user.rol = data['rol']
    if 'password' in data and data['password']:
        user.set_password(data['password'])

    db.session.commit()
    return jsonify({'user': user.to_dict()})


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    current_id = int(get_jwt_identity())
    if user.id == current_id:
        return jsonify({'error': 'No puedes eliminarte a ti mismo'}), 403

    db.session.delete(user)
    db.session.commit()
    return jsonify({'mensaje': 'Usuario eliminado correctamente'})
