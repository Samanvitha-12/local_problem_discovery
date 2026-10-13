import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

if os.environ.get("RENDER"):
    INSTANCE_DIR = "/var/data"
else:
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

os.makedirs(INSTANCE_DIR, exist_ok=True)

DEFAULT_DATABASE_PATH = os.path.join(
    INSTANCE_DIR, "problem_alert.db"
).replace("\\", "/")



class Config:
    ENVIRONMENT = os.environ.get('FLASK_ENV', 'development').lower()
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-secret')
    # Prefer DATABASE_URI from environment (e.g., mysql+pymysql://user:pass@host/db).
    # The local fallback is the one persistent application database, rather
    # than a second empty file alongside the backend source.
 SQLALCHEMY_DATABASE_URI = (
    os.environ.get("DATABASE_URI")
    or f"sqlite:///{DEFAULT_DATABASE_PATH}"
)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 1 day
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    FRONTEND_URL = os.environ.get('FRONTEND_URL', '').rstrip('/')
    CORS_ORIGINS = tuple(origin.strip() for origin in os.environ.get('CORS_ORIGINS', FRONTEND_URL).split(',') if origin.strip())
    OFFICIAL_AUTO_APPROVE = os.environ.get('OFFICIAL_AUTO_APPROVE', 'false' if ENVIRONMENT == 'production' else 'true').lower() == 'true'
    OFFICIAL_SETUP_KEY = os.environ.get('OFFICIAL_SETUP_KEY', '')
    ADMIN_SETUP_KEY = os.environ.get('ADMIN_SETUP_KEY', '')
    GOVERNMENT_APPROVAL_CODE = os.environ.get('GOVERNMENT_APPROVAL_CODE', ADMIN_SETUP_KEY)
    # The image validation endpoint reads uploads into memory before YOLO
    # inference, so keep the request bound explicit and predictable.
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MiB

    @classmethod
    def validate_production_settings(cls):
        if cls.ENVIRONMENT != 'production':
            return
        required = {'SECRET_KEY': cls.SECRET_KEY, 'JWT_SECRET_KEY': cls.JWT_SECRET_KEY,
                    'DATABASE_URI': os.environ.get('DATABASE_URI'), 'FRONTEND_URL': cls.FRONTEND_URL,
                    'CORS_ORIGINS': cls.CORS_ORIGINS}
        missing = [name for name, value in required.items() if not value or value in {'change-this-secret', 'replace-with-strong-secret', 'replace-with-strong-jwt-secret'}]
        if missing:
            raise RuntimeError(f"Production configuration is incomplete: {', '.join(missing)}")
