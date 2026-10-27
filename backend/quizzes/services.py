def validate_quiz_data(data):
    if not data:
        return 'Datos requeridos'
    if not data.get('titulo') and not data.get('topic'):
        return 'El título o topic es requerido'
    if not data.get('banco') or not isinstance(data['banco'], list):
        return 'El banco de preguntas es requerido'
    if len(data['banco']) == 0:
        return 'El banco de preguntas no puede estar vacío'
    for i, q in enumerate(data['banco']):
        if not q.get('pregunta'):
            return f'La pregunta {i + 1} no tiene texto'
        if not q.get('opciones') or not isinstance(q['opciones'], list) or len(q['opciones']) < 2:
            return f'La pregunta {i + 1} debe tener al menos 2 opciones'
        if q.get('correcta') is None or not isinstance(q['correcta'], int):
            return f'La pregunta {i + 1} no tiene una respuesta correcta válida'
    return None


def validate_submit_data(data):
    if not data:
        return 'Datos requeridos'
    if not data.get('nombre') or not data['nombre'].strip():
        return 'El nombre del estudiante es requerido'
    if not data.get('documento') or not data['documento'].strip():
        return 'El documento del estudiante es requerido'
    if not data.get('respuestas') or not isinstance(data['respuestas'], list):
        return 'Las respuestas son requeridas'
    if len(data['respuestas']) == 0:
        return 'Debe haber al menos una respuesta'
    return None
