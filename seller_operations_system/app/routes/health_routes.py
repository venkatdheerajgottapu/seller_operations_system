import sys
import platform
import importlib.metadata
from flask import Blueprint, jsonify, render_template

from database.connection import check_db_connection
from app.config import Config

health_bp = Blueprint('health', __name__)


def get_version(package_name: str) -> str:
    """Safely get package version using importlib.metadata."""
    try:
        return importlib.metadata.version(package_name)
    except Exception:
        return "installed"


def get_system_diagnostics():
    """Aggregate environment and library diagnostics."""
    db_status = check_db_connection()
    return {
        "status": "HEALTHY" if db_status.get("connected") else "ATTENTION_REQUIRED",
        "environment": {
            "python_version": sys.version.split()[0],
            "os": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "mysql_host": Config.DB_HOST,
            "mysql_port": Config.DB_PORT,
            "mysql_user": Config.DB_USER,
            "mysql_database": Config.DB_NAME,
        },
        "packages": {
            "flask": get_version("flask"),
            "sqlalchemy": get_version("sqlalchemy"),
            "pandas": get_version("pandas"),
            "mysql_connector": get_version("mysql-connector-python"),
            "faker": get_version("faker"),
            "pytest": get_version("pytest"),
        },
        "database": db_status
    }


@health_bp.route('/api/health', methods=['GET'])
def api_health():
    """JSON API endpoint for system health verification."""
    diagnostics = get_system_diagnostics()
    status_code = 200 if diagnostics["status"] == "HEALTHY" else 503
    return jsonify(diagnostics), status_code


@health_bp.route('/health', methods=['GET'])
def health_page():
    """Visual Phase 1 Verification Dashboard."""
    diagnostics = get_system_diagnostics()
    return render_template('health.html', diagnostics=diagnostics)
