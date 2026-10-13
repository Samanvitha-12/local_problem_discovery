import json
import threading
from pathlib import Path

from models import db, Notification, Official, Admin, Complaint, ComplaintHistory, EmergencyAlert, Department, ComplaintStatus, DeadlineExtensionRequest
from datetime import datetime, timedelta

EMERGENCY_DATASET_PATH = Path(__file__).resolve().parents[1] / 'datasets' / 'emergency' / 'india_emergency_numbers.json'

# Every category is mapped to a real, dialable India emergency service. The
# dataset's municipal entries say "Varies by city", so they cannot be used by
# the Call action.
def get_emergency_contacts_for_category(category):
    category_name = (category or '').strip().lower()
    default_contact = {'service': 'Emergency Response (Police, Fire, Ambulance, Rescue)', 'number': '112',
                       'description': 'Pan-India emergency helpline', 'channels': ['call', 'sms'],
                       'source': 'https://112.gov.in/'}

    if not EMERGENCY_DATASET_PATH.exists():
        return [default_contact]

    try:
        with EMERGENCY_DATASET_PATH.open('r', encoding='utf-8') as handle:
            contacts = json.load(handle)
    except (OSError, ValueError):
        return [default_contact]

    selected = []
    for contact in contacts:
        mapped_categories = {str(item).strip().lower() for item in contact.get('categories', [])}
        is_universal = contact.get('service') == default_contact['service']
        if (category_name in mapped_categories or is_universal and not selected) and str(contact.get('number', '')).strip().isdigit():
            selected.append({key: contact[key] for key in ('service', 'number', 'category', 'description', 'channels', 'source') if key in contact})
    if not selected:
        return [default_contact]
    return selected


def get_emergency_contact_for_category(category):
    """Return one dialable emergency contact appropriate to the complaint type."""
    return get_emergency_contacts_for_category(category)[0]


def build_alert_message(complaint, analysis):
    priority = analysis.get('priority') or complaint.priority or 'Medium'
    category = complaint.category or 'General'
    if priority == 'Critical':
        return f"Emergency alert: {category} complaint #{complaint.id} requires immediate response. Citizen reported: {complaint.description[:140]}"
    return f"New civic complaint #{complaint.id} ({category}) requires review. Priority: {priority}."


def infer_department_for_category(category):
    normalized = (category or '').strip().lower()
    mapping = {
        'road damage': 'Road Department', 'potholes': 'Road Department',
        'garbage': 'Garbage/Waste Management Department', 'illegal dumping': 'Garbage/Waste Management Department',
        'water leakage': 'Water Supply Department', 'water supply': 'Water Supply Department',
        'drainage': 'Drainage Department', 'drainage blockage': 'Drainage Department', 'flood': 'Drainage Department',
        'street light': 'Street Light Department', 'broken street light': 'Street Light Department',
        'tree fallen': 'Tree/Public Works Department', 'fallen tree': 'Tree/Public Works Department',
        'electricity': 'Electrical Department', 'electric pole damage': 'Electrical Department',
        'fire': 'Fire and Rescue Department', 'medical emergency': 'Health and Ambulance Department',
        'animal issue': 'Animal Welfare Department', 'public property damage': 'Public Works Department',
        'traffic signal': 'Traffic Management Department',
    }
    return mapping.get(normalized, 'General Civic Department')


def assign_complaint_to_official(complaint):
    """Route a case to the best available responsible official.

    Local service-area matches are preferred, then the official with the fewest
    active cases. This keeps new reports evenly distributed instead of always
    selecting the first approved account.
    """
    preferred_department = infer_department_for_category(complaint.category)
    department = Department.query.filter_by(name=preferred_department).first()
    query = Official.query.filter_by(approved=True)
    if department is not None:
        query = query.filter_by(department_id=department.id)
    candidates = query.all() or Official.query.filter_by(approved=True).all()
    if not candidates:
        return None

    reporter = complaint.user
    def assignment_key(official):
        workload = Complaint.query.join(ComplaintStatus).filter(
            Complaint.official_id == official.id,
            ~ComplaintStatus.name.in_(('Resolved', 'Rejected')),
        ).count()
        mismatches = 0
        if reporter:
            mismatches = sum(
                bool(getattr(reporter, field, None)) and getattr(official, field, None) != getattr(reporter, field, None)
                for field in ('district', 'taluk', 'village')
            )
        return (mismatches, workload, official.id)

    official = min(candidates, key=assignment_key)
    complaint.official_id = official.id
    return official


def dispatch_complaint_alerts(complaint, analysis):
    message = build_alert_message(complaint, analysis)
    officials = [complaint.official] if complaint.official else []
    if complaint.priority == 'Critical':
        department = infer_department_for_category(complaint.category)
        officials.extend(Official.query.join(Department).filter(
            Official.approved.is_(True), Department.name == department
        ).all())
    officials = list({official.id: official for official in officials}.values())
    official_ids = []
    for official in officials:
        db.session.add(Notification(official_id=official.id, message=message))
        official_ids.append(official.id)
        # Keep an auditable dispatch record for every assigned case; Critical
        # cases simply fan out to the department as well.
        db.session.add(EmergencyAlert(
            complaint_id=complaint.id,
            official_id=official.id,
            message=message,
            contact_number=official.phone,
            status='queued',
        ))

    admin_accounts = Admin.query.all()
    if admin_accounts:
        for admin in admin_accounts:
            db.session.add(Notification(user_id=None, official_id=None, message=f"Admin alert: {message}"))

    return {
        'message': message,
        'officialCount': len(official_ids),
        'adminCount': len(admin_accounts),
        'emergencyContacts': get_emergency_contacts_for_category(complaint.category),
    }


def create_history_entry(complaint, status_name, note=''):
    entry = ComplaintHistory(complaint_id=complaint.id, status_name=status_name, note=note)
    db.session.add(entry)
    db.session.commit()
    return entry


def _process_overdue_complaints(now=None):
    """Escalate each missed open-case target once and notify all three roles."""
    now = now or datetime.utcnow()
    terminal = {'Resolved', 'Completed', 'Closed', 'Rejected'}
    overdue = Complaint.query.filter(
        Complaint.sla_due_at.isnot(None), Complaint.sla_due_at <= now,
        Complaint.escalated_at.is_(None),
    ).all()
    escalated = []
    status = ComplaintStatus.query.filter_by(name='Escalated').first()
    if status is None and overdue:
        status = ComplaintStatus(name='Escalated', description='Case missed its assigned resolution target and requires administrator review')
        db.session.add(status)
        db.session.flush()
    for complaint in overdue:
        if complaint.status and complaint.status.name in terminal:
            continue
        complaint.escalated_at = now
        complaint.reminder_sent_at = now
        complaint.status = status
        complaint.status_id = status.id
        for request in DeadlineExtensionRequest.query.filter_by(complaint_id=complaint.id, status='Pending').all():
            request.status = 'Expired'
            request.decided_at = now
            request.decision_note = 'The deadline passed before the citizen decided; administrator review is required.'
        hours = complaint.sla_target_hours
        if hours is None and complaint.created_at:
            hours = max(1, round((complaint.sla_due_at - complaint.created_at).total_seconds() / 3600))
        hours = hours or 24
        official_name = complaint.official.full_name if complaint.official else 'Unassigned'
        message = f'Complaint #{complaint.id} ({complaint.category}) was not completed within its {hours}-hour target. Assigned official: {official_name}. Administrator action is required.'
        db.session.add(ComplaintHistory(
            complaint_id=complaint.id, status_name='Escalated',
            note=f'{hours}-hour resolution target missed. Escalated for administrator review.',
        ))
        if complaint.user_id:
            db.session.add(Notification(user_id=complaint.user_id,
                message=f'Complaint #{complaint.id} was not completed by its deadline. The administrator has been notified and will review the assignment.'))
        if complaint.official_id:
            db.session.add(Notification(official_id=complaint.official_id,
                message=f'Complaint #{complaint.id} was not completed by its {hours}-hour deadline. It has been escalated for administrator review.'))
        db.session.add(Notification(user_id=None, official_id=None,
            message=f'Admin action required: {message}'))
        escalated.append(complaint)
    if escalated:
        db.session.commit()
        try:
            from flask import current_app
            socketio = current_app.extensions.get('socketio')
            if socketio:
                for complaint in escalated:
                    socketio.emit('complaint.updated', {'complaint': complaint.to_dict()})
                    socketio.emit('sla.escalated', {'complaintId': complaint.id, 'complaint': complaint.to_dict()})
        except RuntimeError:
            pass
    return escalated


_OVERDUE_PROCESS_LOCK = threading.Lock()


def process_overdue_complaints(now=None):
    """Serialize request-triggered and scheduled escalation scans per worker."""
    if not _OVERDUE_PROCESS_LOCK.acquire(blocking=False):
        return []
    try:
        return _process_overdue_complaints(now)
    finally:
        _OVERDUE_PROCESS_LOCK.release()
