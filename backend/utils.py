import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_jwt_extended import get_jwt, get_jwt_identity

ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'jpe', 'jfif', 'apng', 'webp', 'bmp', 'dib',
    'tif', 'tiff', 'gif', 'avif', 'jp2', 'j2k', 'ico', 'tga',
    'pdf', 'mp4', 'mov', 'webm',
}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, upload_folder: str) -> str:
    filename = file.filename
    if not filename or not allowed_file(filename):
        return None
    filename = secure_filename(filename)
    os.makedirs(upload_folder, exist_ok=True)
    path = os.path.join(upload_folder, filename)
    file.save(path)
    return path


def hash_password(password: str) -> str:
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)


def verify_password(hash_value: str, password: str) -> bool:
    return check_password_hash(hash_value, password)


def make_response_payload(message: str, data=None):
    payload = {'message': message}
    if data is not None:
        payload['data'] = data
    return payload


def get_now():
    return datetime.utcnow().isoformat() + 'Z'


def current_identity():
    """Read the role-aware identity stored in standard JWT subject/claims."""
    try:
        claims = get_jwt()
    except RuntimeError:
        claims = {}

    try:
        subject = get_jwt_identity()
    except RuntimeError:
        subject = None

    try:
        account_id = int(subject)
    except (TypeError, ValueError):
        account_id = subject
    return {'id': account_id, 'role': claims.get('role'), 'name': claims.get('name')}
