def test_create_and_public_quiz_security(client, teacher_auth):
    # Crear prueba como profesor
    quiz_payload = {
        'titulo': 'Genética Mendeliana',
        'nivel': 'bachillerato',
        'numQ': 2,
        'bankSize': 2,
        'apoyo': 'Material de apoyo sobre las leyes de Mendel.',
        'banco': [
            {
                'pregunta': '¿Cuál es la primera ley de Mendel?',
                'opciones': ['Uniformidad', 'Segregación', 'Independencia', 'Dominancia incompleta'],
                'correcta': 0,
                'explicacion': 'La primera ley es la ley de la uniformidad de los híbridos de la primera generación.',
                'subtema': 'Leyes de Mendel',
            },
            {
                'pregunta': '¿Qué es un alelo recesivo?',
                'opciones': ['Se expresa en heterocigoto', 'Solo se expresa en homocigosis', 'Es dominante', 'No existe'],
                'correcta': 1,
                'explicacion': 'Un alelo recesivo se enmascara en presencia de un dominante.',
                'subtema': 'Conceptos básicos',
            }
        ]
    }
    create_res = client.post('/api/quizzes', json=quiz_payload, headers=teacher_auth)
    assert create_res.status_code == 201
    quiz_id = create_res.get_json()['quiz']['id']

    # Consultar como estudiante en el endpoint público
    pub_res = client.get(f'/api/public/quizzes/{quiz_id}')
    assert pub_res.status_code == 200
    pub_data = pub_res.get_json()

    assert pub_data['titulo'] == 'Genética Mendeliana'
    assert len(pub_data['banco']) == 2

    # VERIFICACIÓN CRÍTICA DE SEGURIDAD:
    # Las respuestas correctas y explicaciones previas NO deben estar en el JSON público
    for q in pub_data['banco']:
        assert 'correcta' not in q, "¡Fuga de seguridad! 'correcta' encontrada en endpoint público"
        assert 'explicacion' not in q, "¡Fuga de seguridad! 'explicacion' encontrada en endpoint público"


def test_submit_attempt_server_side_grading(client, teacher_auth):
    # Crear prueba
    create_res = client.post('/api/quizzes', json={
        'titulo': 'Ecología Básica',
        'banco': [
            {
                'pregunta': '¿Qué es un productor primario?',
                'opciones': ['Autótrofo', 'Heterótrofo', 'Descomponedor', 'Carroñero'],
                'correcta': 0,
                'explicacion': 'Los autótrofos generan su propio alimento.',
                'subtema': 'Cadenas tróficas',
            }
        ]
    }, headers=teacher_auth)
    quiz_id = create_res.get_json()['quiz']['id']

    # Estudiante intenta hacer trampa enviando selected=1 pero mintiendo con correct=1
    cheating_submission = {
        'nombre': 'Estudiante Tramposo',
        'documento': '12345678',
        'respuestas': [
            {
                'pregunta': '¿Qué es un productor primario?',
                'selected': 1, # INCORRECTO (la correcta es 0)
                'correct': 1,  # Falso intento de trampa
            }
        ]
    }

    sub_res = client.post(f'/api/quizzes/{quiz_id}/submit', json=cheating_submission)
    assert sub_res.status_code == 201
    result = sub_res.get_json()

    # El servidor debió evaluar contra la base de datos: puntaje 0, no 1
    assert result['attempt']['puntaje'] == 0
    assert result['attempt']['porcentaje'] == 0
    assert result['evaluated'][0]['is_correct'] is False
    assert result['evaluated'][0]['correct'] == 0


def test_submit_attempt_deduplication(client, teacher_auth):
    create_res = client.post('/api/quizzes', json={
        'titulo': 'Célula',
        'banco': [
            {
                'pregunta': '¿Función de la mitocondria?',
                'opciones': ['ATP', 'Fotosíntesis', 'Mitosis', 'Digestión'],
                'correcta': 0,
                'subtema': 'Organelos',
            }
        ]
    }, headers=teacher_auth)
    quiz_id = create_res.get_json()['quiz']['id']

    # Primer intento
    client.post(f'/api/quizzes/{quiz_id}/submit', json={
        'nombre': 'Laura Gómez',
        'documento': '98765432',
        'respuestas': [{'selected': 1, 'pregunta': '¿Función de la mitocondria?'}]
    })

    # Segundo intento del mismo documento
    client.post(f'/api/quizzes/{quiz_id}/submit', json={
        'nombre': 'Laura Gómez',
        'documento': '98765432',
        'respuestas': [{'selected': 0, 'pregunta': '¿Función de la mitocondria?'}]
    })

    # Verificar que en los intentos registrados solo hay 1 fila para ese estudiante
    attempts_res = client.get(f'/api/quizzes/{quiz_id}/attempts', headers=teacher_auth)
    attempts = attempts_res.get_json()['attempts']
    assert len(attempts) == 1
    assert attempts[0]['puntaje'] == 1
