import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import create_app, seed_defaults

app = create_app()
with app.app_context():
    seed_defaults(app)
    client = app.test_client()

    # Register a citizen
    payload = {
        'email': 'citizen.test@example.com',
        'fullName': 'Citizen Test',
        'phone': '+911111111111',
        'password': 'Citizen123!'
    }
    r = client.post('/api/auth/register/user', json=payload)
    print('Register user status:', r.status_code, r.get_json())

    # Login to get token
    r2 = client.post('/api/auth/login/user', json={'email': payload['email'], 'password': payload['password']})
    print('Login status:', r2.status_code, r2.get_json())
    token = r2.get_json().get('data', {}).get('accessToken')
    headers = {'Authorization': f'Bearer {token}'}

    # Create a complaint
    complaint = {
        'title': 'Pothole on Test St',
        'category': 'Road Damage',
        'description': 'Large pothole near the main junction',
        'location': 'Test Junction',
        'latitude': '12.9716',
        'longitude': '77.5946',
        'imageCount': 0,
        'nearbyReports': 0
    }
    r3 = client.post('/api/complaints/create', json=complaint, headers=headers)
    print('Create complaint status:', r3.status_code, r3.get_json())

    # List complaints for user
    r4 = client.get('/api/complaints/', headers=headers)
    print('List complaints status:', r4.status_code, r4.get_json())
