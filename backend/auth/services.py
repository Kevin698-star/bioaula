import re

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def validate_registration(data):
    if not data:
        return 'Datos requeridos'
    if not data.get('nombre') or not str(data['nombre']).strip():
        return 'El nombre es requerido'
    if not data.get('correo') or not str(data['correo']).strip():
        return 'El correo es requerido'
    correo = str(data['correo']).strip()
    if not EMAIL_REGEX.match(correo):
        return 'Formato de correo electrónico inválido'
    password = str(data.get('password', ''))
    if len(password) < 8:
        return 'La contraseña debe tener al menos 8 caracteres'
    rol = str(data.get('rol', 'estudiante')).strip().lower()
    # Seguridad crítica: el rol 'admin' JAMÁS puede registrarse por la API pública
    if rol not in ('estudiante', 'profesor'):
        return 'Rol inválido para registro público. Solo estudiante o profesor.'
    return None


def validate_login(data):
    if not data:
        return 'Datos requeridos'
    if not data.get('correo') or not str(data['correo']).strip():
        return 'El correo es requerido'
    if not data.get('password'):
        return 'La contraseña es requerida'
    return None
