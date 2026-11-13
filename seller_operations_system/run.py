import os
from app import create_app
from database.connection import check_db_connection, create_database_if_not_exists, init_db

env_name = os.getenv('FLASK_ENV', 'development')
app = create_app(env_name)

if __name__ == '__main__':
    print("=" * 65)
    print("  SELLER OPERATIONS & PAYOUT INTELLIGENCE PLATFORM")
    print("  Enterprise Dashboard & Settlement Reconciliation Engine")
    print(f"  Active Environment Profile: {env_name.upper()}")
    print("=" * 65)

    # Initialize tables
    init_db()

    # Attempt to verify or create MySQL database if configured
    db_result = create_database_if_not_exists()
    print(f"[DB INIT] {db_result['message']}")

    # Check connection
    conn_status = check_db_connection()
    if conn_status.get('connected'):
        print(f"[DB CONNECTED] Dialect: {conn_status.get('dialect').upper()}, Latency: {conn_status.get('latency_ms')} ms")
        print(f"[DB SERVER VERSION] {conn_status.get('server_version')}")
    else:
        print(f"[DB NOTICE] {conn_status.get('error')}")

    port = int(os.getenv('PORT', '5000'))
    host = os.getenv('HOST', '127.0.0.1')

    if env_name == 'production':
        print(f"\n[PRODUCTION SERVER] Running in PRODUCTION mode on http://{host}:{port} (debug=False)...")
        print("[NOTICE] For Linux / Container production deployments, run: gunicorn -c gunicorn.conf.py wsgi:app")
        try:
            from waitress import serve
            print("Using Waitress high-concurrency WSGI server...")
            serve(app, host=host, port=port)
        except ImportError:
            print("[NOTICE] Waitress not installed, starting Flask engine in non-debug mode:")
            app.run(host=host, port=port, debug=False)
    else:
        print(f"\n[DEV SERVER] Starting local development server on http://{host}:{port} (debug=True)...")
        print("Press Ctrl+C to stop.\n")
        app.run(host=host, port=port, debug=True)
