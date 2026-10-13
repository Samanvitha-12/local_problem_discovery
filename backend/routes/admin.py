from flask import Blueprint, request, jsonify, current_app, Response
from datetime import datetime, timezone, timedelta
import csv
import io
import json
from flask_jwt_extended import jwt_required
from models import db, Official, User, Admin, Department, Complaint, ComplaintStatus, Notification, ComplaintCluster, ComplaintHistory, DeadlineExtensionRequest, Log
from utils import make_response_payload, current_identity
from services.alert_service import process_overdue_complaints

admin_bp = Blueprint('admin', __name__)

def admin_required():
    identity = current_identity()
    if identity.get('role') != 'admin':
        return False
    return True


def audit(action, target, previous=None, new=None):
    """Persist high-impact administrator actions for accountability."""
    actor = current_identity()
    db.session.add(Log(event=f'admin:{action}', details=json.dumps({
        'admin_id': actor.get('id'), 'target': target, 'previous': previous,
        'new': new, 'at': datetime.utcnow().isoformat() + 'Z',
    }, default=str)))

@admin_bp.route('/dashboard', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def admin_dashboard():
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    identity = current_identity()
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    now = datetime.utcnow()
    process_overdue_complaints(now)
    late = [item for item in Complaint.query.filter(
        Complaint.sla_due_at.isnot(None), Complaint.sla_due_at <= now
    ).all() if not item.status or item.status.name not in {'Resolved', 'Completed', 'Closed', 'Rejected'}]
    administrator = Admin.query.get(identity.get('id'))
    return jsonify(make_response_payload('Dashboard loaded', {
        # Identity details are exposed only through this admin-protected route.
        'administrator': administrator.to_dict() if administrator else None,
        'pendingOfficials': [official.to_dict() for official in Official.query.filter_by(approved=False).all()],
        'officials': [official.to_dict() for official in Official.query.order_by(Official.full_name).all()],
        'users': [user.to_dict() for user in User.query.all()],
        'departments': [dept.to_dict() for dept in Department.query.all()],
        'complaints': [complaint.to_dict() for complaint in Complaint.query.order_by(Complaint.created_at.desc()).limit(12)],
        'clusters': [cluster.to_dict() for cluster in ComplaintCluster.query.order_by(ComplaintCluster.created_at.desc()).all()],
        'slaViolations': [complaint.to_dict() for complaint in late],
        'notifications': [note.to_dict() for note in Notification.query.filter_by(user_id=None, official_id=None).order_by(Notification.created_at.desc()).limit(50).all()],
        'statistics': {
            'totalUsers': User.query.count(), 'totalOfficials': Official.query.count(),
            'totalComplaints': Complaint.query.count(), 'overdueComplaints': len(late),
            'criticalComplaints': Complaint.query.filter_by(priority='Critical').count(),
            'resolvedComplaints': Complaint.query.join(ComplaintStatus).filter(ComplaintStatus.name == 'Resolved').count(),
        },
    })), 200

@admin_bp.route('/approve-official/<int:official_id>', methods=['PUT', 'OPTIONS'])
@jwt_required(optional=True)
def approve_official(official_id):
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    official = Official.query.get_or_404(official_id)
    previous = {'approved': official.approved}
    official.approved = True
    audit('approve_official', f'official:{official.id}', previous, {'approved': True})
    db.session.commit()
    return jsonify(make_response_payload('Official approved', {'official': official.to_dict()})), 200

@admin_bp.route('/reject-official/<int:official_id>', methods=['DELETE', 'OPTIONS'])
@jwt_required(optional=True)
def reject_official(official_id):
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    official = Official.query.get_or_404(official_id)
    audit('delete_official', f'official:{official.id}', {'email': official.email, 'department_id': official.department_id})
    db.session.delete(official)
    db.session.commit()
    return jsonify(make_response_payload('Official registration rejected')), 200

@admin_bp.route('/departments', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def create_department():
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    data = request.get_json() or {}
    department = Department(name=data.get('name', '').strip(), description=data.get('description', '').strip())
    db.session.add(department)
    db.session.commit()
    return jsonify(make_response_payload('Department created', {'department': department.to_dict()})), 201

@admin_bp.route('/complaints/<int:complaint_id>/assign', methods=['PUT', 'OPTIONS'])
@jwt_required(optional=True)
def assign_complaint(complaint_id):
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    data = request.get_json() or {}
    complaint = Complaint.query.get_or_404(complaint_id)
    official_id = data.get('officialId')
    official = Official.query.get(official_id) if official_id else None
    if official_id and (official is None or not official.approved):
        return jsonify(make_response_payload('Choose an approved official')), 400
    previous = {'official_id': complaint.official_id, 'status_id': complaint.status_id}
    complaint.official_id = official_id
    complaint.status_id = data.get('statusId', complaint.status_id)
    db.session.add(ComplaintHistory(complaint_id=complaint.id, status_name=complaint.status.name if complaint.status else 'Assigned', note='Administrator reassigned complaint'))
    audit('assign_complaint', f'complaint:{complaint.id}', previous, {'official_id': complaint.official_id, 'status_id': complaint.status_id})
    db.session.commit()
    if complaint.user_id:
        Notification.query.filter_by(user_id=complaint.user_id).delete()
        db.session.add(Notification(user_id=complaint.user_id, message=f'Complaint "{complaint.title}" assigned to official.'))
        db.session.commit()
    return jsonify(make_response_payload('Complaint assigned', {'complaint': complaint.to_dict()})), 200


@admin_bp.route('/officials/<int:official_id>', methods=['PATCH', 'OPTIONS'])
@jwt_required(optional=True)
def manage_official(official_id):
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    official = Official.query.get_or_404(official_id)
    data = request.get_json() or {}
    previous = {'approved': official.approved, 'department_id': official.department_id, 'designation': official.designation}
    if 'departmentId' in data:
        department = Department.query.get(data['departmentId'])
        if not department:
            return jsonify(make_response_payload('Invalid department')), 400
        official.department_id = department.id
    if 'approved' in data:
        official.approved = bool(data['approved'])
    if 'designation' in data:
        official.designation = str(data['designation']).strip()[:120]
    audit('manage_official', f'official:{official.id}', previous,
          {'approved': official.approved, 'department_id': official.department_id, 'designation': official.designation})
    db.session.commit()
    return jsonify(make_response_payload('Official updated', {'official': official.to_dict()})), 200


@admin_bp.route('/complaints/<int:complaint_id>/manage', methods=['PATCH', 'OPTIONS'])
@jwt_required(optional=True)
def manage_complaint(complaint_id):
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    complaint = Complaint.query.get_or_404(complaint_id)
    data = request.get_json() or {}
    previous = {'priority': complaint.priority, 'priority_score': complaint.priority_score,
                'official_id': complaint.official_id, 'sla_target_hours': complaint.sla_target_hours,
                'sla_due_at': complaint.sla_due_at}
    previous_due_at = complaint.sla_due_at
    previous_official_id = complaint.official_id
    was_escalated = bool(complaint.escalated_at)
    if 'priority' in data:
        priority = str(data['priority']).capitalize()
        if priority not in {'Critical', 'High', 'Medium', 'Low'}:
            return jsonify(make_response_payload('Priority must be Critical, High, Medium, or Low')), 400
        complaint.priority = priority
    if 'priorityScore' in data:
        complaint.priority_score = max(0, min(100, int(data['priorityScore'])))
    if 'officialId' in data:
        try:
            requested_official_id = int(data['officialId']) if data['officialId'] else None
        except (TypeError, ValueError):
            return jsonify(make_response_payload('Choose a valid approved official')), 400
        official = Official.query.get(requested_official_id) if requested_official_id else None
        if data['officialId'] and (official is None or not official.approved):
            return jsonify(make_response_payload('Choose an approved official')), 400
        complaint.official_id = official.id if official else None
    if 'deadline' in data:
        try:
            parsed = datetime.fromisoformat(str(data['deadline']).replace('Z', '+00:00'))
            complaint.sla_due_at = parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
            complaint.sla_target_hours = max(1, round((complaint.sla_due_at - datetime.utcnow()).total_seconds() / 3600))
            if complaint.sla_due_at > datetime.utcnow():
                complaint.reminder_sent_at = None
                complaint.escalated_at = None
                if complaint.status and complaint.status.name == 'Escalated':
                    in_progress = ComplaintStatus.query.filter_by(name='In Progress').first()
                    if in_progress:
                        complaint.status = in_progress
                        complaint.status_id = in_progress.id
        except ValueError:
            return jsonify(make_response_payload('deadline must be a valid ISO-8601 date/time')), 400
    now = datetime.utcnow()
    reassigned = previous_official_id != complaint.official_id
    restart_target = reassigned and complaint.official_id is not None and (was_escalated or (complaint.sla_due_at is not None and complaint.sla_due_at <= now))
    if restart_target:
        if 'deadline' not in data or complaint.sla_due_at is None or complaint.sla_due_at <= now:
            try:
                target_hours = int(data.get('targetHours', 24))
                if not 1 <= target_hours <= 720:
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify(make_response_payload('targetHours must be a whole number from 1 to 720')), 400
            complaint.sla_target_hours = target_hours
            complaint.sla_due_at = now + timedelta(hours=target_hours)
        else:
            complaint.sla_target_hours = max(1, round((complaint.sla_due_at - now).total_seconds() / 3600))
        complaint.escalated_at = None
        complaint.reminder_sent_at = None
        active_status = ComplaintStatus.query.filter_by(name='In Progress').first()
        if active_status:
            complaint.status = active_status
            complaint.status_id = active_status.id
    complaint.updated_at = now
    note = 'Administrator changed complaint controls'
    if previous_official_id != complaint.official_id:
        for extension in DeadlineExtensionRequest.query.filter_by(complaint_id=complaint.id, status='Pending').all():
            extension.status = 'Cancelled'
            extension.decided_at = now
            extension.decision_note = 'The administrator changed the case assignment; this request no longer applies.'
        old_official = Official.query.get(previous_official_id) if previous_official_id else None
        new_official = Official.query.get(complaint.official_id) if complaint.official_id else None
        note = f'Administrator reassigned case from {old_official.full_name if old_official else "Unassigned"} to {new_official.full_name if new_official else "Unassigned"}'
        if restart_target:
            note += f'; new {complaint.sla_target_hours}-hour target set, due {complaint.sla_due_at.isoformat()} UTC'
        if old_official:
            db.session.add(Notification(official_id=old_official.id, message=f'Complaint #{complaint.id} was reassigned by an administrator.'))
        if new_official:
            target_note = f' A new {complaint.sla_target_hours}-hour target is due {complaint.sla_due_at.isoformat()} UTC.' if restart_target else ''
            db.session.add(Notification(official_id=new_official.id, message=f'Complaint #{complaint.id} has been assigned to you by an administrator.{target_note}'))
        if complaint.user_id:
            target_note = f' A new {complaint.sla_target_hours}-hour target is due {complaint.sla_due_at.isoformat()} UTC.' if restart_target else ''
            db.session.add(Notification(user_id=complaint.user_id, message=f'An administrator reassigned complaint #{complaint.id} to another official.{target_note}'))
    elif previous_due_at != complaint.sla_due_at:
        due_note = f'Administrator changed the resolution deadline for complaint #{complaint.id} to {complaint.sla_due_at.isoformat()} UTC.'
        if complaint.official_id:
            db.session.add(Notification(official_id=complaint.official_id, message=due_note))
        if complaint.user_id:
            db.session.add(Notification(user_id=complaint.user_id, message=due_note))
    db.session.add(ComplaintHistory(complaint_id=complaint.id, status_name=complaint.status.name if complaint.status else 'Updated', note=note))
    audit('manage_complaint', f'complaint:{complaint.id}', previous,
          {'priority': complaint.priority, 'priority_score': complaint.priority_score,
           'official_id': complaint.official_id, 'sla_target_hours': complaint.sla_target_hours,
           'sla_due_at': complaint.sla_due_at})
    db.session.commit()
    socketio = current_app.extensions.get('socketio')
    if socketio:
        socketio.emit('complaint.updated', {'complaint': complaint.to_dict()})
    return jsonify(make_response_payload('Complaint controls updated', {'complaint': complaint.to_dict()})), 200


@admin_bp.route('/audit-logs', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def audit_logs():
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    records = Log.query.order_by(Log.created_at.desc()).limit(200).all()
    return jsonify(make_response_payload('Audit logs loaded', {'logs': [record.to_dict() for record in records]})), 200


@admin_bp.route('/export/complaints', methods=['GET'])
@jwt_required(optional=True)
def export_complaints():
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Category', 'Priority', 'Status', 'Location', 'Official ID', 'Created at', 'SLA due at'])
    for item in Complaint.query.order_by(Complaint.created_at.desc()).all():
        writer.writerow([item.id, item.title, item.category, item.priority, item.status.name if item.status else '', item.location, item.official_id or '', item.created_at.isoformat(), item.sla_due_at.isoformat() if item.sla_due_at else ''])
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=complaints.csv'})

@admin_bp.route('/categories', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def list_categories():
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    return jsonify(make_response_payload('Categories loaded', {'categories': [status.to_dict() for status in ComplaintStatus.query.all()]})), 200

@admin_bp.route('/categories', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def create_category():
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    data = request.get_json() or {}
    example = ComplaintStatus(name=data.get('name', '').strip(), description=data.get('description', '').strip())
    db.session.add(example)
    db.session.commit()
    return jsonify(make_response_payload('Category created', {'category': example.to_dict()})), 201

@admin_bp.route('/fake-complaints/<int:complaint_id>', methods=['DELETE', 'OPTIONS'])
@jwt_required(optional=True)
def delete_fake_complaint(complaint_id):
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    if not admin_required():
        return jsonify(make_response_payload('Forbidden')), 403
    complaint = Complaint.query.get_or_404(complaint_id)
    db.session.delete(complaint)
    db.session.commit()
    return jsonify(make_response_payload('Complaint deleted')), 200
