import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


def normalize_database_url(url: str) -> str:
    """Normalize legacy postgres:// scheme to postgresql:// for SQLAlchemy compatibility."""
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key-seller-ops-2026')
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = False
    TESTING = False

    # MySQL connection parameters
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'seller_ops_db')

    # Build MySQL URI safely handling URL-encoded special characters in password
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
    auth_part = f"{DB_USER}:{encoded_password}" if encoded_password else DB_USER
    MYSQL_URI = f"mysql+mysqlconnector://{auth_part}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # Auto-resolve SQLALCHEMY_DATABASE_URI: DATABASE_URL > MySQL (if configured) > Local SQLite
    raw_db_url = os.getenv('DATABASE_URL')
    if raw_db_url:
        SQLALCHEMY_DATABASE_URI = normalize_database_url(raw_db_url)
    elif DB_PASSWORD:
        SQLALCHEMY_DATABASE_URI = MYSQL_URI
    else:
        sqlite_file = BASE_DIR / 'seller_ops_db.sqlite'
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{sqlite_file.as_posix()}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800
    }

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600


class DevelopmentConfig(Config):
    """Development environment configuration."""
    ENV = 'development'
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing configuration with SQLite in-memory database."""
    ENV = 'testing'
    DEBUG = False
    TESTING = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(Config):
    """Production configuration with hardened security and error handling."""
    ENV = 'production'
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')

    # Production connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
        'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20'))
    }


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
