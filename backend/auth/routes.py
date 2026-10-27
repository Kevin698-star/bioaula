from flask import jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from . import auth_bp
from ..models.user import User
from ..extensions import db
from .services import validate_registration, validate_login


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    error = validate_registration(data)
    if error:
        return jsonify({'error': error}), 400

    correo_clean = data['correo'].strip().lower()
    if User.query.filter_by(correo=correo_clean).first():
        return jsonify({'error': 'El correo ya está registrado'}), 409

    # Forzar rol a estudiante o profesor validado (nunca admin por registro público)
    rol = data.get('rol', 'estudiante')
    if rol not in ('estudiante', 'profesor'):
        rol = 'estudiante'

    user = User(
        nombre=data['nombre'].strip(),
        correo=correo_clean,
        rol=rol,
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    error = validate_login(data)
    if error:
        return jsonify({'error': error}), 400

    user = User.query.filter_by(correo=data['correo'].strip().lower()).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()})


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id)) if user_id else None
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify({'user': user.to_dict()})
