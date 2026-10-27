def validate_user_data(data, is_update=False):
    if not data:
        return 'Datos requeridos'

    if not is_update:
        if not data.get('nombre') or not data['nombre'].strip():
            return 'El nombre es requerido'
        if not data.get('correo') or not data['correo'].strip():
            return 'El correo es requerido'
        if not data.get('password') or len(data['password']) < 8:
            return 'La contraseña debe tener al menos 8 caracteres'
        if not data.get('rol') or data['rol'] not in ('admin', 'profesor', 'estudiante'):
            return 'Rol inválido. Debe ser: admin, profesor o estudiante'
        return None

    if 'correo' in data and data['correo']:
        if '@' not in data['correo']:
            return 'Correo inválido'

    if 'password' in data and data['password'] and len(data['password']) < 8:
        return 'La contraseña debe tener al menos 8 caracteres'

    if 'rol' in data and data['rol'] not in ('admin', 'profesor', 'estudiante', None):
        return 'Rol inválido. Debe ser: admin, profesor o estudiante'

    return None
