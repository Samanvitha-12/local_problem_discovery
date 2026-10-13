import secrets
from app import create_app
from models import db, Admin, Department, ComplaintStatus
from utils import hash_password

app = create_app()

with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(email='admin@problemalert.gov').first():
        initial_password = secrets.token_urlsafe(24)
        admin = Admin(full_name='System Administrator', email='admin@problemalert.gov', password_hash=hash_password(initial_password))
        db.session.add(admin)
        print(f'Initial local admin: admin@problemalert.gov / {initial_password}')
    default_departments = [
        {'name': 'Public Works', 'description': 'Infrastructure, street lighting, drainage and civic maintenance'},
        {'name': 'Water Management', 'description': 'Water supply, pipelines, and reservoir maintenance'},
        {'name': 'Sanitation', 'description': 'Waste management, cleaning and public sanitation review'},
        {'name': 'Traffic and Safety', 'description': 'Road safety, traffic signals, and accident prevention'},
    ]
    for department in default_departments:
        if not Department.query.filter_by(name=department['name']).first():
            db.session.add(Department(name=department['name'], description=department['description']))
    default_statuses = ['Submitted', 'In Progress', 'Resolved', 'Escalated']
    for status in default_statuses:
        if not ComplaintStatus.query.filter_by(name=status).first():
            db.session.add(ComplaintStatus(name=status, description=f'{status} status for complaints'))
    db.session.commit()
    print('Sample data seeded successfully.')
