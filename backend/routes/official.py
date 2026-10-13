from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Official, Complaint, ComplaintStatus, Notification, Department, ComplaintHistory, DeadlineExtensionRequest
from services.alert_service import infer_department_for_category
from utils import make_response_payload, current_identity

official_bp = Blueprint('official', __name__)


def assign_pending_department_complaints(official):
    """Persist assignment of legacy/pending reports when an eligible official logs in."""
    department_name = official.department.name if official.department else None
    pending = Complaint.query.filter(Complaint.official_id.is_(None)).order_by(
        Complaint.priority_score.desc(), Complaint.created_at.asc()
    ).all()
    assigned_count = 0
    for complaint in pending:
        # Older generic official accounts did not have a department value. They
        # are the control-room fallback, so they may claim the legacy pending
        # queue rather than leaving submitted complaints invisible forever.
        if department_name and infer_department_for_category(complaint.category) != department_name:
            continue
        complaint.official_id = official.id
        db.session.add(ComplaintHistory(
            complaint_id=complaint.id,
            status_name=complaint.status.name if complaint.status else 'Submitted',
            note=f"Automatically assigned to {official.full_name} from the pending {department_name or 'control-room'} queue",
        ))
        assigned_count += 1
    if assigned_count:
        db.session.commit()
    return assigned_count

@official_bp.route('/profile', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def official_profile():
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    identity = current_identity()
    if not identity.get('id'):
        return jsonify(make_response_payload('Authentication required')), 401
    if identity.get('role') != 'official':
        return jsonify(make_response_payload('Forbidden')), 403
    official = Official.query.get_or_404(identity.get('id'))
    assign_pending_department_complaints(official)

    assigned = Complaint.query.filter(
        Complaint.official_id == official.id
    ).order_by(Complaint.created_at.desc()).all()

    priority_order = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
    assigned = sorted(
        assigned,
        key=lambda item: (item.priority_score or 0, priority_order.get(item.priority, 0), -item.created_at.timestamp()),
        reverse=True,
    )

    return jsonify(make_response_payload('Official dashboard loaded', {
        'official': official.to_dict(),
        'assignedComplaints': [item.to_dict() for item in assigned],
        'complaints': [item.to_dict() for item in assigned],
        'departments': [dept.to_dict() for dept in Department.query.all()],
        'notifications': [note.to_dict() for note in sorted(official.notifications, key=lambda item: item.created_at, reverse=True)[:50]],
    })), 200

@official_bp.route('/assignments', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def official_assignments():
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    identity = current_identity()
    if not identity.get('id'):
        return jsonify(make_response_payload('Authentication required')), 401
    if identity.get('role') != 'official':
        return jsonify(make_response_payload('Forbidden')), 403
    assigned = Complaint.query.filter_by(official_id=identity.get('id')).order_by(
        Complaint.priority_score.desc(), Complaint.created_at.asc()
    ).all()
    return jsonify(make_response_payload('Assigned complaints', {'assigned': [c.to_dict() for c in assigned]})), 200


@official_bp.route('/complaints/<int:complaint_id>/target', methods=['PUT', 'OPTIONS'])
@jwt_required(optional=True)
def set_resolution_target(complaint_id):
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    identity = current_identity()
    if identity.get('role') != 'official':
        return jsonify(make_response_payload('Only officials can set a resolution target')), 403
    official = Official.query.get_or_404(identity.get('id'))
    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.official_id not in (None, official.id):
        return jsonify(make_response_payload('This case is assigned to another official')), 403
    if official.department and infer_department_for_category(complaint.category) != official.department.name:
        return jsonify(make_response_payload('This case is outside your department')), 403
    if complaint.status and complaint.status.name in {'Resolved', 'Completed', 'Closed', 'Rejected'}:
        return jsonify(make_response_payload('A resolution target cannot be changed for a closed case')), 409
    if complaint.escalated_at:
        return jsonify(make_response_payload('This case is escalated. Ask an administrator to set a new target')), 409
    raw_target = (request.get_json() or {}).get('targetHours')
    try:
        target_hours = int(raw_target)
        if isinstance(raw_target, bool) or float(raw_target) != target_hours:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(make_response_payload('targetHours must be a whole number from 1 to 720')), 400
    if target_hours < 1 or target_hours > 720:
        return jsonify(make_response_payload('targetHours must be a whole number from 1 to 720')), 400

    previous_due = complaint.sla_due_at
    now = datetime.utcnow()
    complaint.official_id = official.id
    complaint.sla_target_hours = target_hours
    complaint.sla_due_at = now + timedelta(hours=target_hours)
    complaint.reminder_sent_at = None
    complaint.updated_at = now
    note = f'{official.full_name} set a {target_hours}-hour resolution target; due {complaint.sla_due_at.isoformat()} UTC.'
    db.session.add(ComplaintHistory(complaint_id=complaint.id,
        status_name=complaint.status.name if complaint.status else 'Assigned', note=note))
    if complaint.user_id:
        db.session.add(Notification(user_id=complaint.user_id,
            message=f'Official set a {target_hours}-hour resolution target for complaint #{complaint.id}.'))
    db.session.add(Notification(user_id=None, official_id=None,
        message=f'Official {official.full_name} set a {target_hours}-hour target for complaint #{complaint.id} ({complaint.category}).'))
    db.session.commit()
    socketio = current_app.extensions.get('socketio')
    if socketio:
        socketio.emit('complaint.updated', {'complaint': complaint.to_dict()})
    return jsonify(make_response_payload('Resolution target saved', {
        'complaint': complaint.to_dict(), 'previousDeadline': previous_due.isoformat() + 'Z' if previous_due else None,
    })), 200


@official_bp.route('/complaints/<int:complaint_id>/extension-requests', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def request_deadline_extension(complaint_id):
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    identity = current_identity()
    if identity.get('role') != 'official':
        return jsonify(make_response_payload('Only the assigned official can request more time')), 403
    official = Official.query.get_or_404(identity.get('id'))
    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.official_id != official.id:
        return jsonify(make_response_payload('Only the assigned official can request more time')), 403
    if not complaint.sla_due_at or (complaint.status and complaint.status.name in {'Resolved', 'Completed', 'Closed', 'Rejected'}):
        return jsonify(make_response_payload('A time extension is available only for an open case with a deadline')), 409
    if complaint.escalated_at:
        return jsonify(make_response_payload('This case is already escalated. Contact the administrator to review it')), 409
    data = request.get_json() or {}
    try:
        hours = int(data.get('requestedHours'))
        if isinstance(data.get('requestedHours'), bool) or float(data.get('requestedHours')) != hours or not 1 <= hours <= 720:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(make_response_payload('requestedHours must be a whole number from 1 to 720')), 400
    reason = str(data.get('reason') or '').strip()[:512]
    if len(reason) < 8:
        return jsonify(make_response_payload('Explain why more time is needed (at least 8 characters)')), 400
    pending = DeadlineExtensionRequest.query.filter_by(complaint_id=complaint.id, status='Pending').first()
    if pending:
        return jsonify(make_response_payload('A time extension request is already waiting for the citizen')), 409

    now = datetime.utcnow()
    extension = DeadlineExtensionRequest(complaint_id=complaint.id, official_id=official.id,
        requested_hours=hours, reason=reason, requested_at=now)
    db.session.add(extension)
    db.session.add(ComplaintHistory(complaint_id=complaint.id,
        status_name=complaint.status.name if complaint.status else 'In Progress',
        note=f'{official.full_name} asked the citizen for {hours} more hours: {reason}'))
    if complaint.user_id:
        db.session.add(Notification(user_id=complaint.user_id,
            message=f'Official requested {hours} more hours for complaint #{complaint.id}. Review the request on your complaint page.'))
    db.session.add(Notification(user_id=None, official_id=None,
        message=f'Official {official.full_name} requested {hours} more hours for complaint #{complaint.id}; citizen decision pending.'))
    db.session.commit()
    socketio = current_app.extensions.get('socketio')
    if socketio:
        socketio.emit('complaint.updated', {'complaint': complaint.to_dict()})
    return jsonify(make_response_payload('More-time request sent to the citizen', {
        'request': extension.to_dict(), 'complaint': complaint.to_dict(),
    })), 201
