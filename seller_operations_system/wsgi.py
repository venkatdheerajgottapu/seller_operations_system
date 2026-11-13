import os
from app import create_app

# Default to production environment when started via WSGI server
env_name = os.getenv('FLASK_ENV', 'production')
app = create_app(env_name)

if __name__ == '__main__':
    # Local production simulation runner
    port = int(os.getenv('PORT', '5000'))
    host = os.getenv('HOST', '0.0.0.0')
    print(f"Starting WSGI application via Waitress server on http://{host}:{port} ...")
    try:
        from waitress import serve
        serve(app, host=host, port=port)
    except ImportError:
        print("Waitress not installed. Starting Flask built-in server (not for public production):")
        app.run(host=host, port=port, debug=False)

