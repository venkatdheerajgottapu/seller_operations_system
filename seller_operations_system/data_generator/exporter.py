import os
import json
import csv
from pathlib import Path
from decimal import Decimal
from datetime import datetime

from app.config import BASE_DIR
from data_generator.generator import SyntheticDataGenerator

EXPORTS_DIR = BASE_DIR / 'exports'
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to serialize Decimals and Datetimes."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def export_dataset(generator: SyntheticDataGenerator, prefix: str = 'starter'):
    """Export the synthetic dataset into CSV, JSON, and SQL formats."""
    print(f"Exporting dataset to {EXPORTS_DIR} ...")
    
    # 1. Export CSVs
    export_to_csv(generator)
    
    # 2. Export JSON
    json_path = EXPORTS_DIR / f"dataset_{prefix}.json"
    export_to_json(generator, json_path)
    
    # 3. Export SQL
    sql_path = EXPORTS_DIR / f"seed_{prefix}.sql"
    export_to_sql(generator, sql_path)
    
    print(f"All exports completed successfully in: {EXPORTS_DIR}")


def export_to_csv(generator: SyntheticDataGenerator):
    """Export core tables to CSV files."""
    datasets = {
        'sellers': [s.to_dict() for s in generator.sellers],
        'product_listings': [l.to_dict() for l in generator.listings],
        'customers': [c.to_dict() for c in generator.customers],
        'orders': [o.to_dict() for o in generator.orders],
        'order_lines': [ol.to_dict() for ol in generator.order_lines],
        'fulfillments': [f.to_dict() for f in generator.fulfillments],
        'customer_reviews': [r.to_dict() for r in generator.reviews],
        'disputes': [d.to_dict() for d in generator.disputes],
        'payouts': [p.to_dict() for p in generator.payouts],
        'payout_lines': [pl.to_dict() for pl in generator.payout_lines],
        'commission_rules': [cr.to_dict() for cr in generator.commission_rules],
        'anomalies_ground_truth': [a.to_dict() for a in generator.ground_truth_anomalies]
    }

    for name, rows in datasets.items():
        if not rows:
            continue
        file_path = EXPORTS_DIR / f"{name}.csv"
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(f"Generated {len(datasets)} CSV files in exports/")


def export_to_json(generator: SyntheticDataGenerator, output_path: Path):
    """Export complete dataset as a single structured JSON file."""
    data = {
        'metadata': {
            'seed': generator.seed,
            'exported_at': datetime.utcnow().isoformat(),
            'summary': generator.get_summary()
        },
        'sellers': [s.to_dict() for s in generator.sellers],
        'product_listings': [l.to_dict() for l in generator.listings],
        'customers': [c.to_dict() for c in generator.customers],
        'orders': [o.to_dict() for o in generator.orders],
        'order_lines': [ol.to_dict() for ol in generator.order_lines],
        'fulfillments': [f.to_dict() for f in generator.fulfillments],
        'customer_reviews': [r.to_dict() for r in generator.reviews],
        'disputes': [d.to_dict() for d in generator.disputes],
        'commission_rules': [cr.to_dict() for cr in generator.commission_rules],
        'payouts': [p.to_dict() for p in generator.payouts],
        'payout_lines': [pl.to_dict() for pl in generator.payout_lines],
        'ground_truth_anomalies': [a.to_dict() for a in generator.ground_truth_anomalies]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, cls=CustomJSONEncoder)
    print(f"Exported JSON dataset: {output_path}")


def sql_escape(text_val: str) -> str:
    """Escape single quotes for SQL insertion."""
    if not text_val:
        return ""
    return str(text_val).replace("'", "''")


def export_to_sql(generator: SyntheticDataGenerator, output_path: Path):
    """Generate SQL INSERT statements for MySQL seed loading."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("-- =========================================================\n")
        f.write("-- SELLER OPERATIONS & PAYOUT INTELLIGENCE SYSTEM SEED DATA\n")
        f.write(f"-- Generated: {datetime.utcnow().isoformat()} | Seed: {generator.seed}\n")
        f.write("-- =========================================================\n\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

        # Sellers
        f.write("-- Sellers\n")
        for s in generator.sellers:
            clean_name = sql_escape(s.name)
            f.write(
                f"INSERT INTO sellers (seller_id, name, email, phone, status, rating, "
                f"on_time_shipment_rate, fulfillment_rate, cancellation_rate, return_rate, dispute_rate, reserve_rate, created_at, updated_at) "
                f"VALUES ('{s.seller_id}', '{clean_name}', '{s.email}', '{s.phone}', '{s.status}', "
                f"{s.rating}, {s.on_time_shipment_rate}, {s.fulfillment_rate}, {s.cancellation_rate}, {s.return_rate}, {s.dispute_rate}, {s.reserve_rate}, "
                f"'{s.created_at.strftime('%Y-%m-%d %H:%M:%S')}', '{s.updated_at.strftime('%Y-%m-%d %H:%M:%S')}');\n"
            )
        f.write("\n")

        # Commission Rules
        f.write("-- Commission Rules\n")
        for cr in generator.commission_rules:
            max_c = str(cr.max_commission) if cr.max_commission else "NULL"
            f.write(
                f"INSERT INTO commission_rules (rule_id, category, base_rate, min_commission, max_commission, effective_from, is_active, created_at) "
                f"VALUES ('{cr.rule_id}', '{cr.category}', {cr.base_rate}, {cr.min_commission}, {max_c}, '{cr.effective_from.strftime('%Y-%m-%d %H:%M:%S')}', 1, '{cr.created_at.strftime('%Y-%m-%d %H:%M:%S')}');\n"
            )
        f.write("\n")

        # Payouts
        f.write("-- Payouts\n")
        for p in generator.payouts:
            f.write(
                f"INSERT INTO payouts (payout_id, seller_id, batch_reference, payout_date, status, gross_amount, "
                f"commission_deduction, refund_deduction, dispute_deduction, reserve_hold_amount, adjustments, net_payout_amount, reconciliation_status, created_at, updated_at) "
                f"VALUES ('{p.payout_id}', '{p.seller_id}', '{p.batch_reference}', '{p.payout_date.strftime('%Y-%m-%d %H:%M:%S')}', '{p.status}', "
                f"{p.gross_amount}, {p.commission_deduction}, {p.refund_deduction}, {p.dispute_deduction}, {p.reserve_hold_amount}, {p.adjustments}, {p.net_payout_amount}, '{p.reconciliation_status}', "
                f"'{p.created_at.strftime('%Y-%m-%d %H:%M:%S')}', '{p.updated_at.strftime('%Y-%m-%d %H:%M:%S')}');\n"
            )
        f.write("\n")
        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")

    print(f"Exported SQL seed file: {output_path}")
