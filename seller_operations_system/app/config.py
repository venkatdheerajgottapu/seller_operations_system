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


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key-seller-ops-2026')

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

    # Allow custom override or default to MySQL URI
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', MYSQL_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'connect_args': {
            'connect_timeout': 10
        }
    }


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration with SQLite in-memory database."""
    DEBUG = False
    TESTING = True
    # In-memory SQLite for high-speed, isolated unit test execution
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

