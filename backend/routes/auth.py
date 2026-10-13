from datetime import datetime
import os
import json
import re
import time
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from sqlalchemy import func
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required
from werkzeug.utils import secure_filename
from models import db, User, Official, Admin, Department
from config import Config
from utils import hash_password, verify_password, make_response_payload, current_identity
from services.location_directory import get_location_directory, is_valid_location

auth_bp = Blueprint('auth', __name__)


def _valid_email(value):
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]{2,}", (value or '').strip()))


def _valid_indian_mobile(value):
    return bool(re.fullmatch(r'(?:\+?91)?[6-9]\d{9}', re.sub(r'[\s()-]', '', value or '')))


def _find_account_by_email(email):
    normalized = (email or '').strip().lower()
    if not normalized:
        return None, None
    admin = Admin.query.filter_by(email=normalized).first()
    if admin:
        return admin, 'admin'
    official = Official.query.filter_by(email=normalized).first()
    if official:
        return official, 'official'
    user = User.query.filter_by(email=normalized).first()
    if user:
        return user, 'user'
    return None, None


def create_auth_tokens(payload):
    claims = {'role': payload['role'], 'name': payload['name']}
    subject = str(payload['id'])
    return create_access_token(identity=subject, additional_claims=claims), create_refresh_token(identity=subject, additional_claims=claims)

@auth_bp.route('/google/config', methods=['GET'])
def google_config():
    """Return the public OAuth client ID needed by Google Identity Services."""
    client_id = (Config.GOOGLE_CLIENT_ID or '').strip()
    mode = 'google' if client_id else 'disabled'
    return jsonify(make_response_payload('Google sign-in configuration loaded', {
        'enabled': mode != 'disabled',
        'clientId': client_id,
        'mode': mode,
        'message': 'Google OAuth needs a configured web client ID.' if mode == 'disabled' else '',
    })), 200


@auth_bp.route('/departments', methods=['GET'])
def public_departments():
    """Public registration data; no account or contact data is exposed."""
    departments = Department.query.order_by(Department.name.asc()).all()
    return jsonify(make_response_payload('Departments loaded', {'departments': [item.to_dict() for item in departments]})), 200


@auth_bp.route('/locations', methods=['GET'])
def public_locations():
    """Return official state, district, and sub-district options for registration."""
    return jsonify(make_response_payload('Locations loaded', {'locations': get_location_directory()})), 200


@auth_bp.route('/google', methods=['POST'])
def google_login():
    """Verify a Google Identity Services token and return the app's JWT.

    Requires a verified Google Identity Services ID token and a matching app account.
    """
    data = request.get_json() or {}
    credential = data.get('credential', '')
    if not credential:
        return jsonify(make_response_payload('Missing Google credential')), 400

    if isinstance(credential, str) and credential.startswith('demo:'):
        return jsonify(make_response_payload('Demo Google credentials are not accepted. Configure Google OAuth and use a verified Google account.')), 401

    # Real Google ID token verification path
    if not Config.GOOGLE_CLIENT_ID:
        return jsonify(make_response_payload('Google sign-in is not configured on the server')), 503

    try:
        with urlopen(f'https://oauth2.googleapis.com/tokeninfo?{urlencode({"id_token": credential})}', timeout=10) as response:
            claims = json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        # Google returns 400 for invalid, expired, or wrong-audience tokens.
        # Keep credentials out of logs and distinguish those from an outage.
        current_app.logger.warning('Google token verification rejected a credential (HTTP %s)', exc.code)
        if exc.code >= 500 or exc.code == 429:
            return jsonify(make_response_payload('Google verification is temporarily unavailable. Please try again shortly.')), 503
        return jsonify(make_response_payload('Google rejected this sign-in token. Retry the Google sign-in and confirm the configured web client ID.')), 401
    except (URLError, TimeoutError, OSError) as exc:
        current_app.logger.warning('Google token verification service is unreachable (%s)', type(exc).__name__)
        return jsonify(make_response_payload('The backend could not reach Google to verify sign-in. Check backend internet access and try again.')), 503
    except (ValueError, json.JSONDecodeError):
        current_app.logger.warning('Google token verification returned an unreadable response')
        return jsonify(make_response_payload('Google returned an unreadable verification response. Please try again shortly.')), 503
    except Exception as exc:
        current_app.logger.exception('Unexpected Google token verification error (%s)', type(exc).__name__)
        return jsonify(make_response_payload('Google sign-in verification failed unexpectedly. Please try again.')), 503
    if (claims.get('aud') != Config.GOOGLE_CLIENT_ID
            or claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com')
            or not str(claims.get('exp', '')).isdigit()
            or int(claims['exp']) <= int(time.time())
            or claims.get('email_verified') not in (True, 'true')):
        return jsonify(make_response_payload('Invalid Google sign-in request')), 401
    email = (claims.get('email', '') or '').strip().lower()
    account, role = _find_account_by_email(email)
    requested_role = str(data.get('role') or '').strip().lower()
    if requested_role == 'citizen':
        requested_role = 'user'
    if requested_role not in ('user', 'official', 'admin'):
        return jsonify(make_response_payload('Choose a valid account type for Google sign-in')), 400
    if not account:
        return jsonify(make_response_payload('No account is linked to this Google email. Register first, then sign in with Google.')), 404
    if role != requested_role:
        return jsonify(make_response_payload(f'This Google email is registered as {role}. Use the matching sign-in page.')), 403
    if role == 'official' and not account.approved:
        return jsonify(make_response_payload('Official account awaits admin approval')), 403
    payload = {'role': role, 'id': account.id, 'name': getattr(account, 'full_name', account.email)}
    access, refresh = create_auth_tokens(payload)
    return jsonify(make_response_payload('Google login successful', {'accessToken': access, 'refreshToken': refresh, 'user': payload})), 200
@auth_bp.route('/register/user', methods=['POST'])
def register_user():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    password = data.get('password', '')
    if not is_valid_location(data.get('state'), data.get('district'), data.get('taluk')):
        return jsonify(make_response_payload('Select a valid state, district, and taluk combination')), 400
    if not _valid_email(email):
        return jsonify(make_response_payload('Enter a valid email address')), 400
    if not _valid_indian_mobile(phone):
        return jsonify(make_response_payload('Enter a valid Indian mobile number')), 400
    if len(password) < 8:
        return jsonify(make_response_payload('Password must be at least 8 characters')), 400
    if not (data.get('fullName') or '').strip():
        return jsonify(make_response_payload('Full name is required')), 400
    if User.query.filter_by(email=email).first() or Official.query.filter_by(email=email).first() or Admin.query.filter_by(email=email).first():
        return jsonify(make_response_payload('Email already registered')), 400

    user = User(
        full_name=data.get('fullName', '').strip(),
        email=email,
        phone=re.sub(r'\D', '', phone)[-10:],
        password_hash=hash_password(password),
        state=data.get('state', '').strip(),
        district=data.get('district', '').strip(),
        taluk=data.get('taluk', '').strip(),
        village=data.get('village', '').strip(),
        address=data.get('address', '').strip(),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(make_response_payload('Citizen account created successfully', {'user': user.to_dict()})), 201


@auth_bp.route('/register/admin', methods=['POST'])
def register_admin():
    data = request.get_json() or {}
    approval_code = (data.get('governmentApprovalCode') or data.get('setupKey') or '').strip()
    expected_codes = {
        (getattr(Config, 'ADMIN_SETUP_KEY', '') or '').strip(),
        (getattr(Config, 'GOVERNMENT_APPROVAL_CODE', '') or '').strip(),
    }
    expected_codes.discard('')

    existing_admin = Admin.query.first()
    if existing_admin:
        if not expected_codes:
            return jsonify(make_response_payload('Additional admin registration is disabled. The system owner must configure ADMIN_SETUP_KEY in backend/.env')), 503
        if not approval_code or approval_code not in expected_codes:
            return jsonify(make_response_payload('Enter the government approval code configured by the system owner')), 403
    elif approval_code and approval_code not in expected_codes:
        return jsonify(make_response_payload('The admin setup code is incorrect')), 403

    email = data.get('email', '').strip().lower()
    if not is_valid_location(data.get('state'), data.get('district'), data.get('taluk')):
        return jsonify(make_response_payload('Select a valid state, district, and taluk combination')), 400
    if not _valid_email(email):
        return jsonify(make_response_payload('Enter a valid email address')), 400
    if User.query.filter_by(email=email).first() or Official.query.filter_by(email=email).first() or Admin.query.filter_by(email=email).first():
        return jsonify(make_response_payload('Email already registered')), 400

    full_name = data.get('fullName', '').strip() or email.split('@', 1)[0].replace('.', ' ').title()
    password = data.get('password', '')
    if len(password) < 8:
        return jsonify(make_response_payload('Password must be at least 8 characters')), 400

    admin_id = (data.get('adminId') or '').strip() or f'ADMIN-{int(datetime.utcnow().timestamp())}'
    if Admin.query.filter_by(admin_id=admin_id).first():
        admin_id = f'{admin_id}-{int(datetime.utcnow().timestamp())}'

    phone = (data.get('phone') or '').strip()
    if not _valid_indian_mobile(phone):
        return jsonify(make_response_payload('Enter a valid Indian mobile number')), 400
    phone = re.sub(r'\D', '', phone)[-10:]
    department = (data.get('department') or '').strip() or None

    try:
        admin = Admin(
            admin_id=admin_id,
            email=email,
            phone=phone,
            department=department,
            full_name=full_name,
            password_hash=hash_password(password),
            state=data.get('state', '').strip(),
            district=data.get('district', '').strip(),
            taluk=data.get('taluk', '').strip(),
        )
        db.session.add(admin)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error('Admin registration failed: %s', str(e))
        return jsonify(make_response_payload('Admin registration failed', {'error': str(e)})), 500

    return jsonify(make_response_payload('Admin account created', {'admin': admin.to_dict()})), 201

@auth_bp.route('/upload-identity', methods=['POST'])
def upload_identity_card():
    file = request.files.get('identityCard')
    if not file or not file.filename or not file.filename.rsplit('.', 1)[-1].lower() in {'jpg', 'jpeg', 'jpe', 'jfif', 'png', 'apng', 'webp', 'bmp', 'dib', 'tif', 'tiff', 'gif', 'avif', 'jp2', 'j2k', 'ico', 'tga'}:
        return jsonify(make_response_payload('Upload a supported image identity photo')), 400
    if request.content_length and request.content_length > 5 * 1024 * 1024:
        return jsonify(make_response_payload('Identity photo must be 5 MB or smaller')), 413
    try:
        from PIL import Image
        image = Image.open(file.stream)
        image.verify()
        if image.format not in {'JPEG', 'PNG', 'WEBP', 'BMP', 'DIB', 'TIFF', 'GIF', 'AVIF', 'JPEG2000', 'ICO', 'TGA'}:
            raise ValueError('Unsupported image format')
        file.stream.seek(0)
    except Exception:
        return jsonify(make_response_payload('The uploaded identity photo is not a supported image')), 400
    upload_dir = current_app.config['UPLOAD_FOLDER']
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}-{secure_filename(file.filename)}"
    destination = os.path.join(upload_dir, filename)
    file.save(destination)
    url = f"/uploads/{filename}"
    return jsonify(make_response_payload('Identity card uploaded', {'identityCardUrl': url})), 201

@auth_bp.route('/register/official', methods=['POST'])
def register_official():
    """Register an official. Accepts JSON or multipart/form-data with an optional identityCard file.

    Client may either upload the identity file first (POST /auth/upload-identity) and provide
    identityCardUrl in the JSON, or send a multipart/form-data request with the identityCard file
    included in the same request.
    """
    # Support JSON payload or form-data
    data = {}
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        # Use form values for multipart requests
        data = request.form.to_dict()
    else:
        data = request.get_json() or {}

    official_setup_key = (data.get('setupKey') or '').strip()
    expected_official_setup_key = (getattr(Config, 'OFFICIAL_SETUP_KEY', '') or '').strip()
    if not expected_official_setup_key:
        return jsonify(make_response_payload('Official registration is disabled. The system owner must configure OFFICIAL_SETUP_KEY in backend/.env')), 503
    if not official_setup_key or official_setup_key != expected_official_setup_key:
        return jsonify(make_response_payload('Enter the correct official setup key')), 403

    # Handle optional identity file included in multipart/form-data
    identity_file = request.files.get('identityCard')
    identity_card_url = (data.get('identityCardUrl') or '').strip()
    if identity_file:
        if not identity_file.filename or not identity_file.filename.rsplit('.', 1)[-1].lower() in {'jpg', 'jpeg', 'jpe', 'jfif', 'png', 'apng', 'webp', 'bmp', 'dib', 'tif', 'tiff', 'gif', 'avif', 'jp2', 'j2k', 'ico', 'tga'}:
            return jsonify(make_response_payload('Upload a supported image identity photo')), 400
        try:
            from PIL import Image
            identity_image = Image.open(identity_file.stream)
            identity_image.verify()
            if identity_image.format not in {'JPEG', 'PNG', 'WEBP', 'BMP', 'DIB', 'TIFF', 'GIF', 'AVIF', 'JPEG2000', 'ICO', 'TGA'}:
                raise ValueError('Unsupported image format')
            identity_file.stream.seek(0)
        except Exception:
            return jsonify(make_response_payload('The uploaded identity photo is not a supported image')), 400
        # Validate and save file
        from utils import save_uploaded_file
        saved_path = save_uploaded_file(identity_file, current_app.config['UPLOAD_FOLDER'])
        if not saved_path:
            return jsonify(make_response_payload('Invalid identity file uploaded')), 400
        filename = os.path.basename(saved_path)
        identity_card_url = f"/uploads/{filename}"

    email = (data.get('email') or '').strip().lower()
    phone = (data.get('phone') or '').strip()
    password = data.get('password') or ''
    if not is_valid_location(data.get('state'), data.get('district'), data.get('taluk')):
        return jsonify(make_response_payload('Select a valid state, district, and taluk combination')), 400
    if not _valid_email(email):
        return jsonify(make_response_payload('Enter a valid email address')), 400
    if not _valid_indian_mobile(phone):
        return jsonify(make_response_payload('Enter a valid Indian mobile number')), 400
    if len(password) < 8:
        return jsonify(make_response_payload('Password must be at least 8 characters')), 400
    if not identity_card_url and not identity_file:
        return jsonify(make_response_payload('A photo of the official identity card is required')), 400
    if identity_card_url and not identity_file:
        identity_name = secure_filename(os.path.basename(identity_card_url))
        uploaded_identity = os.path.join(current_app.config['UPLOAD_FOLDER'], identity_name)
        if not identity_card_url.startswith('/uploads/') or not os.path.isfile(uploaded_identity):
            return jsonify(make_response_payload('Upload a valid identity photo before registering')), 400

    # Check for existing accounts
    if User.query.filter_by(email=email).first() or Official.query.filter_by(email=email).first() or Admin.query.filter_by(email=email).first():
        return jsonify(make_response_payload('Email already registered')), 400

    # Provide safe defaults for required fields so client can omit optional details
    full_name = (data.get('fullName') or '').strip() or email.split('@', 1)[0].replace('.', ' ').title()
    phone = re.sub(r'\D', '', phone)[-10:]
    password_hash = hash_password(password)
    district = (data.get('district') or '').strip() or 'Not Provided'
    taluk = (data.get('taluk') or '').strip() or 'Not Provided'
    village = (data.get('village') or '').strip() or 'Not Provided'
    address = (data.get('address') or '').strip() or 'Not Provided'
    employee_id = (data.get('employeeId') or '').strip() or f'EMP-{int(datetime.utcnow().timestamp())}'

    # Ensure employee_id uniqueness: append suffix if collision
    if Official.query.filter_by(employee_id=employee_id).first():
        employee_id = f"{employee_id}-{int(datetime.utcnow().timestamp())}"

    department_id = None
    try:
        if data.get('departmentId') and str(data.get('departmentId')).isdigit():
            department_id = int(data.get('departmentId'))
        elif data.get('departmentId'):
            department = Department.query.filter(func.lower(Department.name) == str(data.get('departmentId')).strip().lower()).first()
            if department is not None:
                department_id = department.id
    except Exception:
        department_id = None

    if not department_id or not Department.query.get(department_id):
        return jsonify(make_response_payload('Select a valid department for official registration')), 400

    designation = (data.get('designation') or '').strip() or 'Official'
    office_address = (data.get('officeAddress') or '').strip() or 'Not Provided'

    try:
        official = Official(
            full_name=full_name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            state=(data.get('state') or '').strip(),
            district=district,
            taluk=taluk,
            village=village,
            address=address,
            employee_id=employee_id,
            department_id=department_id,
            designation=designation,
            office_address=office_address,
            identity_card_url=identity_card_url,
            approved=Config.OFFICIAL_AUTO_APPROVE,
        )
        db.session.add(official)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error('Official registration failed: %s', str(e))
        return jsonify(make_response_payload('Official registration failed', {'error': str(e)})), 500

    return jsonify(make_response_payload('Official registration submitted for admin approval', {'official': official.to_dict()})), 201

@auth_bp.route('/login/<role>', methods=['POST'])
def login(role):
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    user = None
    if role == 'user':
        user = User.query.filter_by(email=email).first()
    elif role == 'official':
        user = Official.query.filter_by(email=email).first()
    elif role == 'admin':
        user = Admin.query.filter_by(email=email).first()
    else:
        return jsonify(make_response_payload('Invalid role specified')), 400

    if user is None:
        return jsonify(make_response_payload('Email or password invalid')), 401

    if not verify_password(user.password_hash, password):
        return jsonify(make_response_payload('Email or password invalid')), 401

    if role == 'official' and not user.approved:
        return jsonify(make_response_payload('Official account awaits admin approval')), 403

    payload = {
        'role': role,
        'id': user.id,
        'name': getattr(user, 'full_name', user.email),
    }
    access, refresh = create_auth_tokens(payload)

    return jsonify(make_response_payload('Login successful', {'accessToken': access, 'refreshToken': refresh, 'user': payload})), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    identity = current_identity()
    access, _ = create_auth_tokens(identity)
    return jsonify(make_response_payload('Token refreshed', {'accessToken': access})), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    for model in (User, Official, Admin):
        account = model.query.filter_by(email=email).first()
        if account:
            # In production, send an email. Here we return a reset-token placeholder.
            reset_token = f"reset-{account.id}-{int(datetime.utcnow().timestamp())}"
            return jsonify(make_response_payload('Password reset token generated', {'resetToken': reset_token})), 200
    return jsonify(make_response_payload('If that email exists, a reset link has been sent')), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    new_password = data.get('password', '')
    if not email or not _valid_email(email):
        return jsonify(make_response_payload('Enter the email address linked to your account')), 400
    if not isinstance(new_password, str) or len(new_password) < 8:
        return jsonify(make_response_payload('Password must be at least 8 characters')), 400
    account = None
    for model in (User, Official, Admin):
        account = model.query.filter_by(email=email).first()
        if account:
            break
    if not account:
        return jsonify(make_response_payload('Account not found')), 404
    account.password_hash = hash_password(new_password)
    db.session.commit()
    return jsonify(make_response_payload('Password reset successful')), 200
