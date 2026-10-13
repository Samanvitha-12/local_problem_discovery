from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Complaint
from utils import make_response_payload, current_identity

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def user_profile():
    if request.method == 'OPTIONS':
        return jsonify(make_response_payload('Preflight OK', {})), 200
    identity = current_identity()
    if not identity.get('id'):
        return jsonify(make_response_payload('Authentication required')), 401
    if identity.get('role') != 'user':
        return jsonify(make_response_payload('Forbidden')), 403
    user = User.query.get_or_404(identity.get('id'))
    complaints = Complaint.query.filter_by(user_id=user.id).order_by(Complaint.created_at.desc()).all()
    notifications = [note.to_dict() for note in user.notifications]
    return jsonify(make_response_payload('Profile loaded', {
        'user': user.to_dict(),
        'complaints': [complaint.to_dict() for complaint in complaints],
        'notifications': notifications,
    })), 200
