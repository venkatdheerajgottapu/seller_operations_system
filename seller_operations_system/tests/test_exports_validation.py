import os
import json
import csv
import hashlib
from pathlib import Path
from app.config import BASE_DIR

EXPORTS_DIR = BASE_DIR / 'exports'

EXPECTED_CSVS = [
    'sellers.csv', 'product_listings.csv', 'customers.csv', 'orders.csv',
    'order_lines.csv', 'fulfillments.csv', 'customer_reviews.csv', 'disputes.csv',
    'payouts.csv', 'payout_lines.csv', 'commission_rules.csv', 'anomalies_ground_truth.csv',
    'seller_status_events.csv', 'listing_status_events.csv', 'order_status_events.csv',
    'fulfillment_events.csv', 'payout_events.csv'
]


def test_csv_exports_exist_and_readable():
    """Verify all 17 CSV export files exist, are non-empty, and have valid headers and rows."""
    for filename in EXPECTED_CSVS:
        filepath = EXPORTS_DIR / filename
        assert filepath.exists(), f"Missing CSV export file: {filename}"
        assert filepath.stat().st_size > 0, f"CSV file {filename} is empty"

        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            assert len(header) > 0, f"CSV {filename} has empty header"
            row_count = sum(1 for _ in reader)
            assert row_count > 0, f"CSV {filename} has no data rows"


def test_isolated_anomaly_exports():
    """Verify separate ground-truth and detected anomaly CSV and JSON export files exist and are isolated."""
    gt_csv = EXPORTS_DIR / 'ground_truth_anomalies.csv'
    gt_json = EXPORTS_DIR / 'ground_truth_anomalies.json'
    det_csv = EXPORTS_DIR / 'detected_anomalies.csv'
    det_json = EXPORTS_DIR / 'detected_anomalies.json'

    for p in [gt_csv, gt_json, det_csv, det_json]:
        assert p.exists(), f"Missing anomaly export file: {p.name}"
        assert p.stat().st_size > 0, f"Anomaly export {p.name} is empty"

    # Verify ground truth records
    with open(gt_json, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
        assert 'ground_truth_anomalies' in gt_data
        assert len(gt_data['ground_truth_anomalies']) == 6
        for r in gt_data['ground_truth_anomalies']:
            assert r['is_ground_truth'] is True
            assert r['detected_by'] == 'GROUND_TRUTH'

    # Verify detected anomaly records
    with open(det_json, 'r', encoding='utf-8') as f:
        det_data = json.load(f)
        assert 'detected_anomalies' in det_data
        assert len(det_data['detected_anomalies']) == 6
        for r in det_data['detected_anomalies']:
            assert r['is_ground_truth'] is False
            assert r['detected_by'] == 'DETECTOR_ENGINE'


def test_manifest_integrity_and_checksums():
    """Verify manifest.json exists, contains metadata, and all recorded SHA-256 hashes match files on disk."""
    manifest_path = EXPORTS_DIR / 'manifest.json'
    assert manifest_path.exists(), "manifest.json missing from exports/"

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    assert 'metadata' in manifest
    assert manifest['metadata']['seed'] == 20261022
    assert manifest['metadata']['algorithm'] == 'SHA-256'
    assert 'files' in manifest
    assert manifest['total_files'] >= 20

    # Validate actual file hash matching
    for filename, info in manifest['files'].items():
        file_path = EXPORTS_DIR / filename
        assert file_path.exists(), f"File {filename} listed in manifest does not exist"
        assert file_path.stat().st_size == info['size_bytes'], f"Size mismatch for {filename}"

        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        assert sha256.hexdigest() == info['sha256'], f"SHA-256 checksum mismatch for {filename}"


def test_json_export_structure():
    """Verify JSON export dataset exists, is valid JSON, and has complete metadata and entity lists."""
    json_path = EXPORTS_DIR / 'dataset_starter.json'
    assert json_path.exists(), "dataset_starter.json missing from exports/"

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert 'metadata' in data
    assert data['metadata']['seed'] == 20261022
    assert 'summary' in data['metadata']

    required_keys = [
        'sellers', 'product_listings', 'customers', 'orders', 'order_lines',
        'fulfillments', 'payouts', 'payout_lines', 'seller_status_events',
        'listing_status_events', 'order_status_events', 'fulfillment_events', 'payout_events'
    ]
    for k in required_keys:
        assert k in data, f"Key '{k}' missing from JSON export"
        assert len(data[k]) > 0, f"Entity list '{k}' in JSON export is empty"


def test_sql_export_syntax():
    """Verify SQL seed file contains valid statements for all 17 tables and foreign key toggles."""
    sql_path = EXPORTS_DIR / 'seed_starter.sql'
    assert sql_path.exists(), "seed_starter.sql missing from exports/"

    with open(sql_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "SET FOREIGN_KEY_CHECKS = 0;" in content
    assert "SET FOREIGN_KEY_CHECKS = 1;" in content
    
    expected_inserts = [
        "INSERT INTO sellers",
        "INSERT INTO customers",
        "INSERT INTO commission_rules",
        "INSERT INTO product_listings",
        "INSERT INTO orders",
        "INSERT INTO order_lines",
        "INSERT INTO fulfillments",
        "INSERT INTO customer_reviews",
        "INSERT INTO disputes",
        "INSERT INTO payouts",
        "INSERT INTO payout_lines",
        "INSERT INTO seller_status_events",
        "INSERT INTO listing_status_events",
        "INSERT INTO order_status_events",
        "INSERT INTO fulfillment_events",
        "INSERT INTO payout_events",
        "INSERT INTO anomalies"
    ]
    for table_insert in expected_inserts:
        assert table_insert in content, f"Missing statement '{table_insert}' in SQL export"
