import logging
from flask import Flask
from app.config import Config, DevelopmentConfig, config_by_name

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory pattern to create and configure the Flask app.
    """
    app = Flask(__name__)
    config_class = config_by_name.get(config_name, DevelopmentConfig)
    app.config.from_object(config_class)

    logger.info(f"Initializing Seller Operations App with config: '{config_name}'")

    # Register blueprints
    from app.routes.health_routes import health_bp
    from app.routes.dashboard_routes import dashboard_bp
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(health_bp)

    return app

