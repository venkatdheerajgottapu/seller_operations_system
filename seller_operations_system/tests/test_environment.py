import sys
import pytest
from app import create_app


def test_python_version():
    """Verify that Python version meets or exceeds 3.10."""
    assert sys.version_info >= (3, 10), f"Python version {sys.version} is below 3.10"


def test_core_dependencies_importable():
    """Verify all core dependencies are installed and can be imported."""
    import flask
    import sqlalchemy
    import pandas
    import faker
    import mysql.connector

    assert flask is not None
    assert sqlalchemy is not None
    assert pandas is not None
    assert faker is not None
    assert mysql.connector is not None


def test_flask_app_creation():
    """Verify Flask application factory creates app in testing configuration."""
    app = create_app('testing')
    assert app is not None
    assert app.config['TESTING'] is True


def test_health_api_endpoint():
    """Verify that /api/health endpoint returns structured JSON."""
    app = create_app('testing')
    with app.test_client() as client:
        response = client.get('/api/health')
        assert response.status_code in (200, 503)
        assert response.is_json
        data = response.get_json()
        assert "environment" in data
        assert "packages" in data
        assert "database" in data
        assert "status" in data


def test_health_html_page():
    """Verify that the visual health page renders properly."""
    app = create_app('testing')
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert "SellerOps & Payout Intelligence" in html
        assert "Phase 1: Environment & MySQL Connection" in html

