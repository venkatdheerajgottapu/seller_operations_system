import os
import pytest
from app import create_app
from app.config import ProductionConfig, DevelopmentConfig, TestingConfig
from database.connection import get_session
from app.models import Seller


@pytest.fixture(scope="module")
def prod_client():
    """Create Flask test client running with production configuration."""
    app = create_app('production')
    app.config['TESTING'] = True  # Enable test client exception catching while preserving prod handlers
    with app.test_client() as client:
        yield client


def test_production_config_properties():
    """Verify production config sets debug=False, testing=False, and session security flags."""
    app = create_app('production')
    assert app.config['DEBUG'] is False
    assert app.config['TESTING'] is False
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


def test_security_headers_present(prod_client):
    """Verify all hardened security headers are returned on production HTTP responses."""
    resp = prod_client.get('/')
    assert resp.status_code == 200
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert resp.headers.get('X-XSS-Protection') == '1; mode=block'
    assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert 'Content-Security-Policy' in resp.headers


def test_production_404_handling(prod_client):
    """Verify custom 404 handler returns friendly HTML for pages and JSON for API."""
    # HTML request
    html_resp = prod_client.get('/non-existent-route-xyz')
    assert html_resp.status_code == 404
    assert b"404 - Page Not Found" in html_resp.data

    # JSON API request
    json_resp = prod_client.get('/api/non-existent-route-xyz')
    assert json_resp.status_code == 404
    json_data = json_resp.get_json()
    assert json_data is not None
    assert json_data['error'] == 'Not Found'
    assert json_data['status_code'] == 404


def test_health_endpoints_production(prod_client):
    """Verify health endpoints respond with HTTP 200 and valid JSON diagnostics."""
    api_resp = prod_client.get('/api/health')
    assert api_resp.status_code == 200
    data = api_resp.get_json()
    assert 'status' in data
    assert data['status'] in ('HEALTHY', 'ATTENTION_REQUIRED')
    assert 'environment' in data
    assert 'database' in data

    page_resp = prod_client.get('/health')
    assert page_resp.status_code == 200
    assert b"System Health" in page_resp.data or b"Environment" in page_resp.data


def test_all_dashboard_routes_production(prod_client):
    """Verify all 10 dashboard UI pages load with HTTP 200 in production mode."""
    routes = [
        '/',
        '/sellers',
        '/listings',
        '/orders',
        '/fulfillments',
        '/disputes',
        '/commissions',
        '/payouts',
        '/anomalies',
        '/reports'
    ]
    for r in routes:
        resp = prod_client.get(r)
        assert resp.status_code == 200, f"Route {r} returned status {resp.status_code}"


def test_data_regeneration_blocked_in_production(prod_client):
    """Verify that destructive synthetic data regeneration is rejected in production."""
    resp = prod_client.post('/reports/regenerate', data={'preset': 'STARTER'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Data regeneration is disabled in production" in resp.data


def test_download_export_security(prod_client):
    """Verify export download path traversal protection."""
    # Attempt directory traversal
    resp = prod_client.get('/exports/download/../../app/config.py')
    assert resp.status_code == 404

    # Non-existent file
    resp_missing = prod_client.get('/exports/download/missing_file.csv')
    assert resp_missing.status_code == 404


def test_wsgi_entrypoint_importable():
    """Verify wsgi.py exports a valid Flask WSGI application callable."""
    import wsgi
    assert hasattr(wsgi, 'app')
    assert callable(wsgi.app)

