import os
import json
import csv
import hashlib
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List

from app.config import BASE_DIR
from data_generator.generator import SyntheticDataGenerator
from database.connection import get_session
from app.models import AnomalyRecord

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


def sql_val(v) -> str:
    """Format a Python value as a safe SQL literal."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    if isinstance(v, datetime):
        return f"'{v.strftime('%Y-%m-%d %H:%M:%S')}'"
    clean_str = str(v).replace("'", "''")
    return f"'{clean_str}'"


def export_dataset(generator: SyntheticDataGenerator, prefix: str = 'starter'):
    """Export the synthetic dataset into CSV, JSON, and SQL formats along with checksum manifest."""
    print(f"Exporting dataset to {EXPORTS_DIR} ...")
    
    # 1. Export CSVs (all 17 tables)
    export_to_csv(generator)
    
    # 2. Export Separate Ground Truth & Detected Anomalies
    export_anomalies(generator)
    
    # 3. Export JSON
    json_path = EXPORTS_DIR / f"dataset_{prefix}.json"
    export_to_json(generator, json_path)
    
    # 4. Export SQL
    sql_path = EXPORTS_DIR / f"seed_{prefix}.sql"
    export_to_sql(generator, sql_path)
    
    # 5. Export Manifest with SHA-256 Checksums
    manifest_path = EXPORTS_DIR / "manifest.json"
    export_manifest(manifest_path, seed=generator.seed, preset=prefix)
    
    print(f"All exports completed successfully in: {EXPORTS_DIR}")


def export_to_csv(generator: SyntheticDataGenerator):
    """Export all 17 system tables to CSV files."""
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
        'anomalies_ground_truth': [a.to_dict() for a in generator.ground_truth_anomalies],
        'seller_status_events': [e.to_dict() for e in generator.seller_events],
        'listing_status_events': [e.to_dict() for e in generator.listing_events],
        'order_status_events': [e.to_dict() for e in generator.order_events],
        'fulfillment_events': [e.to_dict() for e in generator.fulfillment_events],
        'payout_events': [e.to_dict() for e in generator.payout_events]
    }

    for name, rows in datasets.items():
        if not rows:
            continue
        file_path = EXPORTS_DIR / f"{name}.csv"
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(f"Generated {len(datasets)} CSV files in {EXPORTS_DIR}")


def export_anomalies(generator: SyntheticDataGenerator):
    """Export ground truth and detected anomalies into strictly isolated CSV and JSON files."""
    # 1. Ground Truth
    gt_rows = [a.to_dict() for a in generator.ground_truth_anomalies]
    if gt_rows:
        gt_csv = EXPORTS_DIR / "ground_truth_anomalies.csv"
        with open(gt_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=gt_rows[0].keys())
            writer.writeheader()
            writer.writerows(gt_rows)

        gt_json = EXPORTS_DIR / "ground_truth_anomalies.json"
        with open(gt_json, 'w', encoding='utf-8') as f:
            json.dump({'ground_truth_anomalies': gt_rows}, f, indent=2, cls=CustomJSONEncoder)

    # 2. Detected Anomalies
    detected_rows = []
    try:
        from app.services.anomaly_detector import AnomalyDetectorService
        with get_session() as session:
            det_records = session.query(AnomalyRecord).filter(
                AnomalyRecord.detected_by == 'DETECTOR_ENGINE'
            ).all()
            if not det_records:
                detected_rows = AnomalyDetectorService.run_detection_scan()
            else:
                detected_rows = [r.to_dict() for r in det_records]
    except Exception as e:
        print(f"Warning: Could not fetch detector engine records from DB ({e}); running detector scan...")
        from app.services.anomaly_detector import AnomalyDetectorService
        detected_rows = AnomalyDetectorService.run_detection_scan()

    if detected_rows:
        det_csv = EXPORTS_DIR / "detected_anomalies.csv"
        with open(det_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=detected_rows[0].keys())
            writer.writeheader()
            writer.writerows(detected_rows)

        det_json = EXPORTS_DIR / "detected_anomalies.json"
        with open(det_json, 'w', encoding='utf-8') as f:
            json.dump({'detected_anomalies': detected_rows}, f, indent=2, cls=CustomJSONEncoder)

    print("Exported isolated ground truth and detected anomalies files.")


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
        'ground_truth_anomalies': [a.to_dict() for a in generator.ground_truth_anomalies],
        'seller_status_events': [e.to_dict() for e in generator.seller_events],
        'listing_status_events': [e.to_dict() for e in generator.listing_events],
        'order_status_events': [e.to_dict() for e in generator.order_events],
        'fulfillment_events': [e.to_dict() for e in generator.fulfillment_events],
        'payout_events': [e.to_dict() for e in generator.payout_events]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, cls=CustomJSONEncoder)
    print(f"Exported comprehensive JSON dataset: {output_path}")


def export_to_sql(generator: SyntheticDataGenerator, output_path: Path):
    """Generate complete SQL INSERT statements for all relational entities and events."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("-- =========================================================\n")
        f.write("-- SELLER OPERATIONS & PAYOUT INTELLIGENCE SYSTEM SEED DATA\n")
        f.write(f"-- Generated: {datetime.utcnow().isoformat()} | Seed: {generator.seed}\n")
        f.write("-- =========================================================\n\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

        # 1. Sellers
        f.write("-- Sellers\n")
        for s in generator.sellers:
            f.write(
                f"INSERT INTO sellers (seller_id, name, email, phone, status, rating, "
                f"on_time_shipment_rate, fulfillment_rate, cancellation_rate, return_rate, dispute_rate, reserve_rate, created_at, updated_at) "
                f"VALUES ({sql_val(s.seller_id)}, {sql_val(s.name)}, {sql_val(s.email)}, {sql_val(s.phone)}, {sql_val(s.status)}, "
                f"{sql_val(s.rating)}, {sql_val(s.on_time_shipment_rate)}, {sql_val(s.fulfillment_rate)}, {sql_val(s.cancellation_rate)}, {sql_val(s.return_rate)}, {sql_val(s.dispute_rate)}, {sql_val(s.reserve_rate)}, "
                f"{sql_val(s.created_at)}, {sql_val(s.updated_at)});\n"
            )
        f.write("\n")

        # 2. Customers
        f.write("-- Customers\n")
        for c in generator.customers:
            f.write(
                f"INSERT INTO customers (customer_id, name, email, phone, shipping_address, city, state, postal_code, created_at) "
                f"VALUES ({sql_val(c.customer_id)}, {sql_val(c.name)}, {sql_val(c.email)}, {sql_val(c.phone)}, {sql_val(c.shipping_address)}, {sql_val(c.city)}, {sql_val(c.state)}, {sql_val(c.postal_code)}, {sql_val(c.created_at)});\n"
            )
        f.write("\n")

        # 3. Commission Rules
        f.write("-- Commission Rules\n")
        for cr in generator.commission_rules:
            f.write(
                f"INSERT INTO commission_rules (rule_id, category, base_rate, min_commission, max_commission, effective_from, is_active, created_at) "
                f"VALUES ({sql_val(cr.rule_id)}, {sql_val(cr.category)}, {sql_val(cr.base_rate)}, {sql_val(cr.min_commission)}, {sql_val(cr.max_commission)}, {sql_val(cr.effective_from)}, 1, {sql_val(cr.created_at)});\n"
            )
        f.write("\n")

        # 4. Product Listings
        f.write("-- Product Listings\n")
        for l in generator.listings:
            f.write(
                f"INSERT INTO product_listings (listing_id, seller_id, sku, title, category, price, stock_quantity, status, created_at, updated_at) "
                f"VALUES ({sql_val(l.listing_id)}, {sql_val(l.seller_id)}, {sql_val(l.sku)}, {sql_val(l.title)}, {sql_val(l.category)}, {sql_val(l.price)}, {sql_val(l.stock_quantity)}, {sql_val(l.status)}, {sql_val(l.created_at)}, {sql_val(l.updated_at)});\n"
            )
        f.write("\n")

        # 5. Orders
        f.write("-- Orders\n")
        for o in generator.orders:
            f.write(
                f"INSERT INTO orders (order_id, customer_id, order_date, order_status, payment_status, total_gross_amount, shipping_fee, tax_amount, created_at, updated_at) "
                f"VALUES ({sql_val(o.order_id)}, {sql_val(o.customer_id)}, {sql_val(o.order_date)}, {sql_val(o.order_status)}, {sql_val(o.payment_status)}, {sql_val(o.total_gross_amount)}, {sql_val(o.shipping_fee)}, {sql_val(o.tax_amount)}, {sql_val(o.created_at)}, {sql_val(o.updated_at)});\n"
            )
        f.write("\n")

        # 6. Order Lines
        f.write("-- Order Lines\n")
        for ol in generator.order_lines:
            f.write(
                f"INSERT INTO order_lines (order_line_id, order_id, listing_id, seller_id, quantity, unit_price, line_total, commission_rate, commission_amount, status, created_at) "
                f"VALUES ({sql_val(ol.order_line_id)}, {sql_val(ol.order_id)}, {sql_val(ol.listing_id)}, {sql_val(ol.seller_id)}, {sql_val(ol.quantity)}, {sql_val(ol.unit_price)}, {sql_val(ol.line_total)}, {sql_val(ol.commission_rate)}, {sql_val(ol.commission_amount)}, {sql_val(ol.status)}, {sql_val(ol.created_at)});\n"
            )
        f.write("\n")

        # 7. Fulfillments
        f.write("-- Fulfillments\n")
        for f_rec in generator.fulfillments:
            f.write(
                f"INSERT INTO fulfillments (fulfillment_id, order_line_id, order_id, seller_id, tracking_number, carrier, status, shipped_at, estimated_delivery, delivered_at, is_delayed, delay_days, created_at, updated_at) "
                f"VALUES ({sql_val(f_rec.fulfillment_id)}, {sql_val(f_rec.order_line_id)}, {sql_val(f_rec.order_id)}, {sql_val(f_rec.seller_id)}, {sql_val(f_rec.tracking_number)}, {sql_val(f_rec.carrier)}, {sql_val(f_rec.status)}, {sql_val(f_rec.shipped_at)}, {sql_val(f_rec.estimated_delivery)}, {sql_val(f_rec.delivered_at)}, {sql_val(f_rec.is_delayed)}, {sql_val(f_rec.delay_days)}, {sql_val(f_rec.created_at)}, {sql_val(f_rec.updated_at)});\n"
            )
        f.write("\n")

        # 8. Customer Reviews
        f.write("-- Customer Reviews\n")
        for r in generator.reviews:
            f.write(
                f"INSERT INTO customer_reviews (review_id, order_line_id, seller_id, listing_id, customer_id, rating, comment, created_at) "
                f"VALUES ({sql_val(r.review_id)}, {sql_val(r.order_line_id)}, {sql_val(r.seller_id)}, {sql_val(r.listing_id)}, {sql_val(r.customer_id)}, {sql_val(r.rating)}, {sql_val(r.comment)}, {sql_val(r.created_at)});\n"
            )
        f.write("\n")

        # 9. Disputes
        f.write("-- Disputes\n")
        for d in generator.disputes:
            f.write(
                f"INSERT INTO disputes (dispute_id, order_id, order_line_id, seller_id, customer_id, dispute_type, status, claim_amount, deduction_amount, resolution_date, created_at, updated_at) "
                f"VALUES ({sql_val(d.dispute_id)}, {sql_val(d.order_id)}, {sql_val(d.order_line_id)}, {sql_val(d.seller_id)}, {sql_val(d.customer_id)}, {sql_val(d.dispute_type)}, {sql_val(d.status)}, {sql_val(d.claim_amount)}, {sql_val(d.deduction_amount)}, {sql_val(d.resolution_date)}, {sql_val(d.created_at)}, {sql_val(d.updated_at)});\n"
            )
        f.write("\n")

        # 10. Payouts
        f.write("-- Payouts\n")
        for p in generator.payouts:
            f.write(
                f"INSERT INTO payouts (payout_id, seller_id, batch_reference, payout_date, status, gross_amount, "
                f"commission_deduction, refund_deduction, dispute_deduction, reserve_hold_amount, adjustments, net_payout_amount, reconciliation_status, created_at, updated_at) "
                f"VALUES ({sql_val(p.payout_id)}, {sql_val(p.seller_id)}, {sql_val(p.batch_reference)}, {sql_val(p.payout_date)}, {sql_val(p.status)}, "
                f"{sql_val(p.gross_amount)}, {sql_val(p.commission_deduction)}, {sql_val(p.refund_deduction)}, {sql_val(p.dispute_deduction)}, {sql_val(p.reserve_hold_amount)}, {sql_val(p.adjustments)}, {sql_val(p.net_payout_amount)}, {sql_val(p.reconciliation_status)}, "
                f"{sql_val(p.created_at)}, {sql_val(p.updated_at)});\n"
            )
        f.write("\n")

        # 11. Payout Lines
        f.write("-- Payout Lines\n")
        for pl in generator.payout_lines:
            f.write(
                f"INSERT INTO payout_lines (payout_line_id, payout_id, order_line_id, dispute_id, line_type, amount, description, created_at) "
                f"VALUES ({sql_val(pl.payout_line_id)}, {sql_val(pl.payout_id)}, {sql_val(pl.order_line_id)}, {sql_val(pl.dispute_id)}, {sql_val(pl.line_type)}, {sql_val(pl.amount)}, {sql_val(pl.description)}, {sql_val(pl.created_at)});\n"
            )
        f.write("\n")

        # 12. Seller Events
        f.write("-- Seller Status Events\n")
        for se in generator.seller_events:
            f.write(
                f"INSERT INTO seller_status_events (seller_id, previous_status, new_status, reason, event_timestamp) "
                f"VALUES ({sql_val(se.seller_id)}, {sql_val(se.previous_status)}, {sql_val(se.new_status)}, {sql_val(se.reason)}, {sql_val(se.event_timestamp)});\n"
            )
        f.write("\n")

        # 13. Listing Events
        f.write("-- Listing Status Events\n")
        for le in generator.listing_events:
            f.write(
                f"INSERT INTO listing_status_events (listing_id, previous_status, new_status, reason, event_timestamp) "
                f"VALUES ({sql_val(le.listing_id)}, {sql_val(le.previous_status)}, {sql_val(le.new_status)}, {sql_val(le.reason)}, {sql_val(le.event_timestamp)});\n"
            )
        f.write("\n")

        # 14. Order Events
        f.write("-- Order Status Events\n")
        for oe in generator.order_events:
            f.write(
                f"INSERT INTO order_status_events (order_id, previous_status, new_status, reason, event_timestamp) "
                f"VALUES ({sql_val(oe.order_id)}, {sql_val(oe.previous_status)}, {sql_val(oe.new_status)}, {sql_val(oe.reason)}, {sql_val(oe.event_timestamp)});\n"
            )
        f.write("\n")

        # 15. Fulfillment Events
        f.write("-- Fulfillment Events\n")
        for fe in generator.fulfillment_events:
            f.write(
                f"INSERT INTO fulfillment_events (fulfillment_id, event_type, location, notes, event_timestamp) "
                f"VALUES ({sql_val(fe.fulfillment_id)}, {sql_val(fe.event_type)}, {sql_val(fe.location)}, {sql_val(fe.notes)}, {sql_val(fe.event_timestamp)});\n"
            )
        f.write("\n")

        # 16. Payout Events
        f.write("-- Payout Events\n")
        for pe in generator.payout_events:
            f.write(
                f"INSERT INTO payout_events (payout_id, previous_status, new_status, note, event_timestamp) "
                f"VALUES ({sql_val(pe.payout_id)}, {sql_val(pe.previous_status)}, {sql_val(pe.new_status)}, {sql_val(pe.note)}, {sql_val(pe.event_timestamp)});\n"
            )
        f.write("\n")

        # 17. Ground Truth Anomalies
        f.write("-- Ground Truth Anomalies\n")
        for a in generator.ground_truth_anomalies:
            f.write(
                f"INSERT INTO anomalies (scenario_id, scenario_name, entity_type, entity_id, detected_by, is_ground_truth, severity, description, details, created_at) "
                f"VALUES ({sql_val(a.scenario_id)}, {sql_val(a.scenario_name)}, {sql_val(a.entity_type)}, {sql_val(a.entity_id)}, {sql_val(a.detected_by)}, {sql_val(a.is_ground_truth)}, {sql_val(a.severity)}, {sql_val(a.description)}, {sql_val(a.details)}, {sql_val(a.created_at)});\n"
            )
        f.write("\n")

        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")

    print(f"Exported complete SQL seed file: {output_path}")


def export_manifest(output_path: Path, seed: int = 20261022, preset: str = 'starter'):
    """Generate cryptographic SHA-256 checksum manifest and row count catalog for all export files."""
    manifest = {
        'metadata': {
            'system': 'Seller Operations & Payout Intelligence Platform',
            'export_preset': preset.upper(),
            'seed': seed,
            'generated_at': datetime.utcnow().isoformat(),
            'algorithm': 'SHA-256'
        },
        'files': {}
    }

    for file_path in sorted(EXPORTS_DIR.glob('*.*')):
        if file_path.name == 'manifest.json':
            continue

        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)

        file_info: Dict[str, Any] = {
            'sha256': sha256.hexdigest(),
            'size_bytes': file_path.stat().st_size
        }

        # Row counts for CSV / lines for others
        if file_path.suffix.lower() == '.csv':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    file_info['row_count'] = sum(1 for _ in reader)
                    file_info['columns'] = len(header) if header else 0
            except Exception:
                pass
        elif file_path.suffix.lower() == '.json':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    jdata = json.load(f)
                    if isinstance(jdata, dict):
                        file_info['keys'] = list(jdata.keys())
            except Exception:
                pass

        manifest['files'][file_path.name] = file_info

    manifest['total_files'] = len(manifest['files'])

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"Exported cryptographic manifest: {output_path} ({len(manifest['files'])} files hashed)")
