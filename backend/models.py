from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(24), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    state = db.Column(db.String(120), nullable=True)
    district = db.Column(db.String(100), nullable=False)
    taluk = db.Column(db.String(100), nullable=False)
    village = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    complaints = db.relationship('Complaint', back_populates='user')
    notifications = db.relationship('Notification', back_populates='user')

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'state': self.state,
            'district': self.district,
            'taluk': self.taluk,
            'village': self.village,
            'address': self.address,
            'created_at': self.created_at.isoformat() + 'Z'
        }

class Official(db.Model):
    __tablename__ = 'officials'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(24), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    state = db.Column(db.String(120), nullable=True)
    district = db.Column(db.String(100), nullable=False)
    taluk = db.Column(db.String(100), nullable=False)
    village = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(256), nullable=False)
    employee_id = db.Column(db.String(64), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    designation = db.Column(db.String(120), nullable=False)
    office_address = db.Column(db.String(256), nullable=False)
    identity_card_url = db.Column(db.String(256), nullable=True)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    complaints = db.relationship('Complaint', back_populates='official')
    notifications = db.relationship('Notification', back_populates='official')
    emergency_alerts = db.relationship('EmergencyAlert', back_populates='official')

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'state': self.state,
            'district': self.district,
            'taluk': self.taluk,
            'village': self.village,
            'address': self.address,
            'employee_id': self.employee_id,
            'department_id': self.department_id,
            'department': self.department.to_dict() if self.department else None,
            'designation': self.designation,
            'office_address': self.office_address,
            'identity_card_url': self.identity_card_url,
            'approved': self.approved,
            'created_at': self.created_at.isoformat() + 'Z'
        }

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(24), nullable=True)
    department = db.Column(db.String(120), nullable=True)
    state = db.Column(db.String(120), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    taluk = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'department': self.department,
            'state': self.state,
            'district': self.district,
            'taluk': self.taluk,
            'created_at': self.created_at.isoformat() + 'Z'
        }

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.String(256), nullable=True)
    officials = db.relationship('Official', backref='department', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description}

class ComplaintStatus(db.Model):
    __tablename__ = 'complaint_status'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.String(256), nullable=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description}

class Complaint(db.Model):
    __tablename__ = 'complaints'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(24), nullable=False, default='Normal')
    priority_score = db.Column(db.Integer, nullable=False, default=0)
    location = db.Column(db.String(256), nullable=False)
    latitude = db.Column(db.String(64), nullable=True)
    longitude = db.Column(db.String(64), nullable=True)
    status_id = db.Column(db.Integer, db.ForeignKey('complaint_status.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    official_id = db.Column(db.Integer, db.ForeignKey('officials.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    remarks = db.Column(db.String(512), nullable=True)
    # Evidence and service-level fields are deliberately persisted with the case,
    # making every decision auditable after reassignment or escalation.
    ai_category = db.Column(db.String(120), nullable=True)
    ai_confidence = db.Column(db.Float, nullable=True)
    sla_target_hours = db.Column(db.Integer, nullable=True)
    sla_due_at = db.Column(db.DateTime, nullable=True)
    reminder_sent_at = db.Column(db.DateTime, nullable=True)
    escalated_at = db.Column(db.DateTime, nullable=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('complaint_clusters.id'), nullable=True)
    completion_images = db.relationship('Image', backref='complaint', lazy=True)
    history_entries = db.relationship('ComplaintHistory', backref='complaint', lazy=True, order_by='ComplaintHistory.created_at')

    user = db.relationship('User', back_populates='complaints')
    official = db.relationship('Official', back_populates='complaints')
    status = db.relationship('ComplaintStatus')

    def to_dict(self):
        from services.alert_service import infer_department_for_category, get_emergency_contact_for_category
        department_name = infer_department_for_category(self.category)
        target_hours = self.sla_target_hours
        if target_hours is None and self.sla_due_at and self.created_at:
            target_hours = max(1, round((self.sla_due_at - self.created_at).total_seconds() / 3600))
        if self.official and self.official.department:
            department_name = self.official.department.name
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'description': self.description,
            'priority': self.priority,
            'priority_score': self.priority_score,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'status': self.status.name if self.status else None,
            'user_id': self.user_id,
            'official_id': self.official_id,
            'department_name': department_name,
            'department': {'name': department_name},
            'emergency_contact': get_emergency_contact_for_category(self.category),
            'citizen_name': self.user.full_name if self.user else None,
            'citizen_phone': self.user.phone if self.user else None,
            'remarks': self.remarks,
            'ai_category': self.ai_category,
            'ai_confidence': self.ai_confidence,
            'sla_target_hours': target_hours,
            'sla_due_at': self.sla_due_at.isoformat() + 'Z' if self.sla_due_at else None,
            'reminder_sent_at': self.reminder_sent_at.isoformat() + 'Z' if self.reminder_sent_at else None,
            'escalated_at': self.escalated_at.isoformat() + 'Z' if self.escalated_at else None,
            'cluster_id': self.cluster_id,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z',
            'completion_images': [image.to_dict() for image in self.completion_images],
            'history': [entry.to_dict() for entry in self.history_entries],
            'extension_requests': [item.to_dict() for item in DeadlineExtensionRequest.query.filter_by(complaint_id=self.id).order_by(DeadlineExtensionRequest.requested_at.desc()).all()],
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    official_id = db.Column(db.Integer, db.ForeignKey('officials.id'), nullable=True)
    message = db.Column(db.String(256), nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='notifications')
    official = db.relationship('Official', back_populates='notifications')

    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'read': self.read,
            'user_id': self.user_id,
            'official_id': self.official_id,
            'created_at': self.created_at.isoformat() + 'Z'
        }


class ComplaintHistory(db.Model):
    __tablename__ = 'complaint_history'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    status_name = db.Column(db.String(64), nullable=False)
    note = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'complaint_id': self.complaint_id,
            'status_name': self.status_name,
            'note': self.note,
            'created_at': self.created_at.isoformat() + 'Z',
        }


class DeadlineExtensionRequest(db.Model):
    __tablename__ = 'deadline_extension_requests'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False, index=True)
    official_id = db.Column(db.Integer, db.ForeignKey('officials.id'), nullable=False)
    requested_hours = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='Pending')
    decision_note = db.Column(db.String(512), nullable=True)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        official = Official.query.get(self.official_id)
        return {
            'id': self.id,
            'complaint_id': self.complaint_id,
            'official_id': self.official_id,
            'official_name': official.full_name if official else None,
            'requested_hours': self.requested_hours,
            'reason': self.reason,
            'status': self.status,
            'decision_note': self.decision_note,
            'requested_at': self.requested_at.isoformat() + 'Z' if self.requested_at else None,
            'decided_at': self.decided_at.isoformat() + 'Z' if self.decided_at else None,
        }


class EmergencyAlert(db.Model):
    __tablename__ = 'emergency_alerts'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    official_id = db.Column(db.Integer, db.ForeignKey('officials.id'), nullable=True)
    message = db.Column(db.String(512), nullable=False)
    contact_number = db.Column(db.String(24), nullable=True)
    status = db.Column(db.String(32), nullable=False, default='queued')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    official = db.relationship('Official', back_populates='emergency_alerts')

    def to_dict(self):
        return {
            'id': self.id,
            'complaint_id': self.complaint_id,
            'official_id': self.official_id,
            'message': self.message,
            'contact_number': self.contact_number,
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z',
        }

class Image(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    url = db.Column(db.String(256), nullable=False)
    phase = db.Column(db.String(64), nullable=True)
    media_type = db.Column(db.String(16), nullable=False, default='image')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'complaint_id': self.complaint_id, 'url': self.url, 'phase': self.phase, 'media_type': self.media_type, 'uploaded_at': self.uploaded_at.isoformat() + 'Z'}


class EvidenceValidation(db.Model):
    """AI image validation audit. Revalidations are recorded on unsubmitted evidence."""
    __tablename__ = 'evidence_validations'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    selected_category = db.Column(db.String(120), nullable=False)
    detected_category = db.Column(db.String(120), nullable=True)
    candidate_category = db.Column(db.String(120), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    image_path = db.Column(db.String(256), nullable=True)
    preview_path = db.Column(db.String(256), nullable=True)
    content_sha256 = db.Column(db.String(64), nullable=False, unique=True)
    validation_status = db.Column(db.String(16), nullable=False)
    message = db.Column(db.String(512), nullable=False)
    model_version = db.Column(db.String(128), nullable=True)
    predicted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'complaint_id': self.complaint_id, 'selected_category': self.selected_category,
                'detected_category': self.detected_category, 'confidence': self.confidence,
                'candidate_category': self.candidate_category,
                'image_path': self.image_path, 'preview_path': self.preview_path,
                'validation_status': self.validation_status, 'message': self.message,
                'model_version': self.model_version, 'predicted_at': self.predicted_at.isoformat() + 'Z'}


class ComplaintCluster(db.Model):
    __tablename__ = 'complaint_clusters'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius_meters = db.Column(db.Integer, nullable=False, default=200)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    complaints = db.relationship('Complaint', backref='cluster', lazy=True)

    def to_dict(self):
        cases = self.complaints or []
        return {'id': self.id, 'category': self.category, 'latitude': self.latitude, 'longitude': self.longitude,
                'radius_meters': self.radius_meters, 'complaint_count': len(cases),
                'average_priority_score': round(sum(c.priority_score for c in cases) / len(cases), 1) if cases else 0,
                'created_at': self.created_at.isoformat() + 'Z'}

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(256), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'event': self.event, 'details': self.details, 'created_at': self.created_at.isoformat() + 'Z'}
