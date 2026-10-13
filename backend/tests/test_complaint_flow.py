import os
import shutil
import sys
import tempfile
import unittest


class ComplaintFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='civic-alert-', dir='c:/7thMajor/backend')
        self.db_path = os.path.join(self.tmpdir, 'test.db')
        os.environ['DATABASE_URI'] = f'sqlite:///{self.db_path}'
        os.environ['SECRET_KEY'] = 'test-secret'
        os.environ['JWT_SECRET_KEY'] = 'test-secret'
        sys.path.insert(0, 'c:/7thMajor/backend')
        import app as app_module
        self.app_module = app_module
        self.app = app_module.create_app()
        self.app.config['TESTING'] = True
        self.app_module.seed_defaults(self.app)
        with self.app.app_context():
            from models import db, User, Official
            db.session.query(Official).delete()
            db.session.query(User).delete()
            db.session.commit()
            user = User(
                full_name='Test Citizen',
                email='citizen@example.com',
                phone='+919999999999',
                password_hash=self.app_module.hash_password('password123'),
                district='Test District',
                taluk='Test Taluk',
                village='Test Village',
                address='Test Address',
            )
            official = Official(
                full_name='Test Official',
                email='official@example.com',
                phone='+919999999998',
                password_hash=self.app_module.hash_password('password123'),
                district='Test District',
                taluk='Test Taluk',
                village='Test Village',
                address='Test Address',
                employee_id='EMP-TEST-1',
                designation='Engineer',
                office_address='Test Office',
                approved=True,
            )
            db.session.add_all([user, official])
            db.session.commit()
            self.user_id = user.id
            self.official_id = official.id

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def valid_validation_id(self, category):
        """Create a completed YOLO audit for complaint-flow tests.

        Detector inference itself is covered separately; these tests exercise
        the downstream workflow only after the production gate has accepted
        evidence.
        """
        with self.app.app_context():
            from models import db, EvidenceValidation
            validation = EvidenceValidation(
                user_id=self.user_id, selected_category=category,
                detected_category=category, confidence=96.4,
                content_sha256=f'{category}-{os.urandom(24).hex()}',
                validation_status='valid', message='Image validated successfully.',
                model_version='best.pt',
            )
            db.session.add(validation)
            db.session.commit()
            return validation.id

    def test_user_profile_preflight_returns_success(self):
        client = self.app.test_client()
        response = client.options('/api/user/profile')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['message'], 'Preflight OK')

    def test_complaint_without_a_validated_image_is_rejected(self):
        client = self.app.test_client()
        login_resp = client.post('/api/auth/login/user', json={
            'email': 'citizen@example.com', 'password': 'password123',
        })
        token = login_resp.get_json()['data']['accessToken']
        with self.app.app_context():
            from models import Complaint
            before = Complaint.query.count()
        response = client.post('/api/complaints/create', json={
            'title': 'Road pothole', 'category': 'Road Damage',
            'description': 'A dangerous pothole needs repair.', 'location': 'Main Road',
        }, headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 422)
        with self.app.app_context():
            self.assertEqual(Complaint.query.count(), before)

    def test_user_profile_includes_user_complaints(self):
        client = self.app.test_client()
        login_resp = client.post('/api/auth/login/user', json={
            'email': 'citizen@example.com',
            'password': 'password123',
        })
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.get_json()['data']['accessToken']

        complaint_response = client.post('/api/complaints/create', json={
            'title': 'Broken street light',
            'category': 'Street Light',
            'description': 'A street light is broken and dangerous at night.',
            'location': 'Main Road',
            'latitude': '12.34',
            'longitude': '77.89',
            'validation_id': self.valid_validation_id('Street Light'),
        }, headers={'Authorization': f'Bearer {token}'})
        complaint_id = complaint_response.get_json()['data']['complaint']['id']

        profile_response = client.get('/api/user/profile', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(profile_response.status_code, 200)
        complaint_ids = [item['id'] for item in profile_response.get_json()['data']['complaints']]
        self.assertIn(complaint_id, complaint_ids)

    def test_complaint_submission_assigns_official_and_persists_alerts(self):
        client = self.app.test_client()
        login_resp = client.post('/api/auth/login/user', json={
            'email': 'citizen@example.com',
            'password': 'password123',
        })
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.get_json()['data']['accessToken']

        response = client.post('/api/complaints/create', json={
            'title': 'Broken street light',
            'category': 'Street Light',
            'description': 'A street light is broken and dangerous at night.',
            'location': 'Main Road',
            'latitude': '12.34',
            'longitude': '77.89',
            'validation_id': self.valid_validation_id('Street Light'),
        }, headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()['data']
        complaint_id = payload['complaint']['id']

        with self.app.app_context():
            from models import Complaint, EmergencyAlert, Notification
            complaint = Complaint.query.get(complaint_id)
            self.assertIsNotNone(complaint)
            self.assertEqual(complaint.official_id, self.official_id)
            self.assertGreaterEqual(EmergencyAlert.query.filter_by(complaint_id=complaint_id).count(), 1)
            self.assertGreaterEqual(Notification.query.filter_by(official_id=self.official_id).count(), 1)

    def test_official_can_accept_reject_and_update_progress_with_photo(self):
        client = self.app.test_client()
        user_login = client.post('/api/auth/login/user', json={
            'email': 'citizen@example.com',
            'password': 'password123',
        })
        citizen_token = user_login.get_json()['data']['accessToken']
        complaint_response = client.post('/api/complaints/create', json={
            'title': 'Broken water pipeline',
            'category': 'Water Leakage',
            'description': 'Water is leaking heavily from a main pipe.',
            'location': 'Bhubaneshwar Road',
            'latitude': '12.99',
            'longitude': '77.99',
            'validation_id': self.valid_validation_id('Water Leakage'),
        }, headers={'Authorization': f'Bearer {citizen_token}'})
        complaint_id = complaint_response.get_json()['data']['complaint']['id']

        official_login = client.post('/api/auth/login/official', json={
            'email': 'official@example.com',
            'password': 'password123',
        })
        official_token = official_login.get_json()['data']['accessToken']

        accept_response = client.put(f'/api/complaints/{complaint_id}/update', json={
            'action': 'accept',
            'remarks': 'Accepted for inspection.'
        }, headers={'Authorization': f'Bearer {official_token}'})
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.get_json()['data']['complaint']['status'], 'Accepted')

        reject_response = client.put(f'/api/complaints/{complaint_id}/update', json={
            'action': 'reject',
            'remarks': 'Area is outside current jurisdiction.'
        }, headers={'Authorization': f'Bearer {official_token}'})
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.get_json()['data']['complaint']['status'], 'Rejected')

        progress_response = client.post(f'/api/complaints/{complaint_id}/progress', json={
            'statusName': 'In Progress',
            'remarks': 'Repair team has reached the site.',
            'completionImages': ['/uploads/progress-1.jpg']
        }, headers={'Authorization': f'Bearer {official_token}'})
        self.assertEqual(progress_response.status_code, 200)
        self.assertEqual(progress_response.get_json()['data']['complaint']['status'], 'In Progress')
        evidence = progress_response.get_json()['data']['complaint']['completion_images']
        self.assertTrue(evidence)
        self.assertEqual(evidence[0]['phase'], 'In Progress')


if __name__ == '__main__':
    unittest.main()
