import os
import uuid
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, render_template
from app.config import Config, DevelopmentConfig, config_by_name, BASE_DIR

# Root logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def configure_logging(app: Flask):
    """Configure structured console and rotating file logging for production."""
    log_level = logging.DEBUG if app.config.get('DEBUG') else logging.INFO
    app.logger.setLevel(log_level)

    # In testing mode, avoid creating file handlers
    if app.config.get('TESTING'):
        return

    logs_dir = BASE_DIR / 'logs'
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            logs_dir / 'app.log',
            maxBytes=10 * 1024 * 1024,  # 10 MB per log file
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] [%(process)d]: %(message)s'
        ))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not initialize rotating file logger: {e}")


def register_error_handlers(app: Flask):
    """Register custom error handlers with clean JSON and HTML negotiation."""

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found on this server.',
                'status_code': 404,
                'path': request.path
            }), 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        error_id = str(uuid.uuid4())[:8]
        app.logger.error(f"[Incident {error_id}] Internal Server Error on {request.method} {request.path}: {e}", exc_info=True)

        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'error': 'Internal Server Error',
                'error_id': error_id,
                'message': 'An unexpected server error occurred. Please contact the platform administrator.',
                'status_code': 500
            }), 500
        return render_template('500.html', error_id=error_id), 500

    @app.errorhandler(403)
    def handle_forbidden(e):
        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource.',
                'status_code': 403
            }), 403
        return render_template('404.html'), 403


def register_security_headers(app: Flask):
    """Inject hardened HTTP response security headers."""

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Basic Content Security Policy allowing required Bootstrap and Chart.js CDNs
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' https: 'unsafe-inline' 'unsafe-eval'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https: data:; "
            "style-src 'self' https: 'unsafe-inline';"
        )
        return response


def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory pattern to create and configure the Flask app.
    """
    app = Flask(__name__)
    config_class = config_by_name.get(config_name, DevelopmentConfig)
    app.config.from_object(config_class)

    logger.info(f"Initializing Seller Operations App with config: '{config_name}' (DEBUG={app.config.get('DEBUG')})")

    # Configure logging, error handlers and security
    configure_logging(app)
    register_error_handlers(app)
    register_security_headers(app)

    # Register blueprints
    from app.routes.health_routes import health_bp
    from app.routes.dashboard_routes import dashboard_bp
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(health_bp)

    return app
