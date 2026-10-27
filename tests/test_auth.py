def test_register_student_success(client):
    res = client.post('/api/auth/register', json={
        'nombre': 'Estudiante Uno',
        'correo': 'estudiante1@bioaula.edu.co',
        'password': 'password123',
        'rol': 'estudiante',
    })
    assert res.status_code == 201
    data = res.get_json()
    assert 'token' in data
    assert data['user']['rol'] == 'estudiante'


def test_register_rejects_admin_role_escalation(client):
    # Intento malicioso de crear admin públicamente
    res = client.post('/api/auth/register', json={
        'nombre': 'Hacker Admin',
        'correo': 'hacker@bioaula.edu.co',
        'password': 'password123',
        'rol': 'admin',
    })
    assert res.status_code == 400
    data = res.get_json()
    assert 'error' in data


def test_register_rejects_short_password(client):
    res = client.post('/api/auth/register', json={
        'nombre': 'Test Corto',
        'correo': 'corto@bioaula.edu.co',
        'password': '12345',
        'rol': 'estudiante',
    })
    assert res.status_code == 400
    assert 'al menos 8 caracteres' in res.get_json()['error']


def test_login_success(client):
    client.post('/api/auth/register', json={
        'nombre': 'Usuario Login',
        'correo': 'login@bioaula.edu.co',
        'password': 'password123',
        'rol': 'estudiante',
    })
    res = client.post('/api/auth/login', json={
        'correo': 'login@bioaula.edu.co',
        'password': 'password123',
    })
    assert res.status_code == 200
    assert 'token' in res.get_json()


def test_login_invalid_password(client):
    client.post('/api/auth/register', json={
        'nombre': 'Usuario Login 2',
        'correo': 'login2@bioaula.edu.co',
        'password': 'password123',
        'rol': 'estudiante',
    })
    res = client.post('/api/auth/login', json={
        'correo': 'login2@bioaula.edu.co',
        'password': 'wrongpassword',
    })
    assert res.status_code == 401
