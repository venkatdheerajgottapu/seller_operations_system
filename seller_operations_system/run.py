import os
from app import create_app
from database.connection import check_db_connection, create_database_if_not_exists, init_db

env_name = os.getenv('FLASK_ENV', 'development')
app = create_app(env_name)

if __name__ == '__main__':
    print("=" * 65)
    print("  SELLER OPERATIONS & PAYOUT INTELLIGENCE PLATFORM")
    print("  Enterprise Dashboard & Settlement Reconciliation Engine")
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

    print("\nStarting Seller Operations Web Dashboard on http://127.0.0.1:5000 ...")
    print("Press Ctrl+C to stop the development server.\n")
    app.run(host='127.0.0.1', port=5000, debug=True)

