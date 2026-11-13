import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_engine, get_session, Base, check_db_connection, create_database_if_not_exists
from app.models import Seller, ProductListing, Customer, Order, OrderLine, Fulfillment, Dispute, Payout
from data_generator.generator import SyntheticDataGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s')


def initialize_schema():
    """Create all database tables if they do not already exist (idempotent, never overwrites)."""
    engine = get_engine()
    print(f"Connecting to database via dialect: {engine.dialect.name.upper()}...")
    Base.metadata.create_all(bind=engine)
    print(f"Schema initialized successfully. {len(Base.metadata.tables)} tables verified.")


def seed_database_if_empty(preset: str = 'STARTER', force: bool = False):
    """Seed synthetic data only if the database is currently empty."""
    with get_session() as session:
        existing_sellers = session.query(Seller).count()
        if existing_sellers > 0 and not force:
            print(f"[SKIP SEEDING] Database already contains {existing_sellers} sellers. Existing data preserved.")
            return False

        print(f"Seeding database with preset '{preset}'...")
        gen = SyntheticDataGenerator()
        gen.generate(preset)
        gen.save_to_db()
        print(f"[SEED SUCCESS] Populated database with preset '{preset}'.")
        return True


def run():
    parser = argparse.ArgumentParser(description="Seller Operations Database Deployment & Initialization Utility")
    parser.add_argument('--check', action='store_true', help="Check database connection and latency")
    parser.add_argument('--seed', action='store_true', help="Seed database if empty")
    parser.add_argument('--preset', default='STARTER', choices=['STARTER', 'MEDIUM', 'FULL'], help="Seed preset (STARTER, MEDIUM, FULL)")
    parser.add_argument('--force-seed', action='store_true', help="Force seed even if data exists (destructive)")

    args = parser.parse_args()

    # Step 1: Health / Connectivity Check
    conn_info = check_db_connection()
    if args.check:
        print("Database Connection Status:")
        for k, v in conn_info.items():
            print(f"  {k}: {v}")
        return

    # Step 2: Initialize Tables
    initialize_schema()

    # Step 3: Seed if requested
    if args.seed:
        seed_database_if_empty(preset=args.preset, force=args.force_seed)


if __name__ == '__main__':
    run()

