import io
import os
import sys
# Ensure repository root (backend folder) is on sys.path so app can be imported when running this script
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import create_app, seed_defaults

app = create_app()
with app.app_context():
    seed_defaults(app)
    client = app.test_client()

    print('--- JSON registration test ---')
    payload = {
        'email': 'official.test@example.com',
        'fullName': 'Test Official',
        'phone': '+911234567890',
        'password': 'Password123!',
        'district': 'Test District',
        'taluk': 'Test Taluk',
        'village': 'Test Village',
        'address': '123 Test St',
        'employeeId': 'EMP-TEST-001',
        'designation': 'Inspector',
        'officeAddress': 'Office 1'
    }
    r = client.post('/api/auth/register/official', json=payload)
    print('Status:', r.status_code)
    print('Response:', r.get_json())

    print('\n--- Multipart registration test with identity file ---')
    data = {
        'email': 'official.file@example.com',
        'fullName': 'File Official',
        'phone': '+919999999998',
        'password': 'Password123!',
        'district': 'File District',
        'taluk': 'File Taluk',
        'village': 'File Village',
        'address': '456 File Ave',
        'employeeId': 'EMP-TEST-002',
        'designation': 'Supervisor',
        'officeAddress': 'Office 2'
    }
    # Proper multipart via test client using werkzeug FileStorage
    from werkzeug.datastructures import FileStorage
    file_storage = FileStorage(stream=io.BytesIO(b'Test file content'), filename='id_test.pdf', content_type='application/pdf')
    multipart_data = dict(**data)
    multipart_data['identityCard'] = file_storage
    r3 = client.post('/api/auth/register/official', data=multipart_data, content_type='multipart/form-data')
    print('Status (multipart):', r3.status_code)
    print('Response (multipart):', r3.get_json())

    # Check duplicate email handling
    print('\n--- Duplicate email test (should fail) ---')
    r4 = client.post('/api/auth/register/official', json=payload)
    print('Status (duplicate):', r4.status_code)
    print('Response (duplicate):', r4.get_json())
