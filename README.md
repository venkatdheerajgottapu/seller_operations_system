# Seller Operations & Payout Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.1.8-red.svg)](https://www.sqlalchemy.org/)
[![Pytest](https://img.shields.io/badge/Pytest-58%20Passed-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An enterprise-grade marketplace seller operations, multi-seller fulfillment, settlement calculation, and financial anomaly intelligence platform built with **Python 3**, **Flask**, **SQLAlchemy**, **Pandas**, **Bootstrap 5**, and **Chart.js**.

---

## 1. Project Overview & Business Problem

In high-volume e-commerce marketplaces, single shopping cart orders frequently contain products sourced from multiple independent third-party merchants. This introduces complex operational challenges:
- **Split Fulfillment Logistics:** Tracking independent parcel shipments, carrier handoffs, and fulfillment delays across diverse seller SLAs.
- **Dynamic Commission Accounting:** Calculating category-based platform fees with minimum fee floors ($0.50 / $1.00) and maximum fee caps ($150.00).
- **Financial Reconciliation & Settlement:** Computing bi-weekly disbursements while accounting for refunds, chargebacks, customer disputes, reserve holds, and eligible adjustments.
- **Anomaly Intelligence:** Detecting operational failures—such as premature payouts on in-transit orders, duplicate commission charges, suspended sellers listing active products, and payout total discrepancies—before disbursements leave the platform.

The **Seller Operations & Payout Intelligence Platform** automates this entire lifecycle with mathematical precision and comprehensive relational auditing.

---

## 2. Core Features

- **Multi-Seller Order Splitting:** Customer checkout carts automatically decompose into line-item fulfillments assigned to distinct sellers with individual carrier tracking numbers (FedEx, UPS, DHL, BlueDart, USPS).
- **SLA Derivation Engine:** Continuously derives seller quality scores (on-time delivery rate, fulfillment rate, dispute rate, return rate) directly from event milestone logs.
- **Settlement Disbursement Formula:**
  $$\text{Net Payout} = \text{Gross Sales} - \text{Commission} - \text{Refunds} - \text{Dispute Deductions} - \text{Reserve Holds} + \text{Eligible Adjustments}$$
  Strictly computed using fixed-point `DECIMAL(12, 2)` arithmetic.
- **Rule-Based Anomaly Detector:** Monitors 5 business invariants independently of ground-truth labels, achieving **100% precision, 100% recall, and 1.0 F1-score** across enterprise datasets.
- **Cryptographic Export Pipeline:** Exports all 17 relational database tables to CSV, isolated anomaly datasets, comprehensive JSON datasets, universal SQL seeds, and a SHA-256 cryptographic manifest.
- **Interactive Management Dashboard:** Real-time metrics, charts, seller directories, order timelines, dispute resolutions, and payout audit pages.

---

## 3. Technology Stack

- **Backend:** Python 3.12+ / 3.14 (Flask 3.1.3, Werkzeug 3.1.8)
- **Database & ORM:** SQLAlchemy 2.1.8, SQLite / PostgreSQL 15+ / MySQL 8.0
- **Data & Testing:** Pandas 3.0.3, Faker 40.54.0, Pytest 9.2.0 (58 automated tests)
- **Frontend & Visualizations:** HTML5, Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Chart.js 4.4.2
- **Production Servers:** Gunicorn 22.0+ (Linux/Containers), Waitress 3.0+ (Windows/Local)
- **Containerization & Deployment:** Docker, Docker Compose, Render Blueprint (`render.yaml`)

---

## 4. Setup & Installation Instructions

### Step 1: Clone Repository
```bash
git clone https://github.com/venkatdheerajgottapu/seller_operations_system.git
cd seller_operations_system/seller_operations_system
```

### Step 2: Configure Environment
```bash
# Optional: create virtual environment
python -m venv .venv

# Enable access to system packages if on Windows Application Control
# or install directly from requirements:
python -m pip install -r requirements.txt
```

---

## 5. FULL Dataset Generation Command

The system includes pre-calibrated generation presets. To generate the enterprise **FULL** dataset using deterministic seed `20261022`:

```bash
python database/init_db.py --seed --preset FULL
```

### Expected Preset Volumes:
- **Sellers:** 2,000
- **Product Listings:** 20,000
- **Orders:** 100,000
- **Disputes:** 10,000
- **Customers:** 8,000
- **Order Lines:** 195,290
- **Fulfillments:** 189,403
- **Reviews:** 62,338
- **Payouts:** 11,307
- **Payout Lines:** 339,238
- **Event Audit Logs:** 970,458
- **Total Records:** 1,908,045 across all 17 tables

> [!NOTE]
> Database seeding is non-destructive by default. If existing records are detected, initialization skips to protect data. Use `--check` to verify database connectivity and row counts without modifying tables.

---

## 6. Testing Command

Execute the complete automated test suite (58 passing tests):

```bash
python -m pytest -v
```

### Test Suite Breakdown:
- `test_database_integrity.py` (13 tests): Schema constraints, PK uniqueness, FK references, transaction rollback.
- `test_db_connection.py` (3 tests): Engine lifecycle, session scopes, error handling.
- `test_environment.py` (5 tests): Python version, dependency imports, Flask app creation, health probes.
- `test_exports_validation.py` (6 tests): CSV headers, anomaly isolation, manifest SHA-256 checksums, JSON structure, SQL DDL/DML, FULL exports.
- `test_financial_reconciliation.py` (4 tests): Full dataset payout formula, header-to-line reconciliation, commission fee bounds, dispute accounting.
- `test_integration.py` (11 tests): End-to-end dashboard routes, seller SLA recalculation, order splitting, fulfillment delays, anomaly detection.
- `test_production_deployment.py` (8 tests): Security headers, 404 handlers, production config, export download traversal defense, WSGI entrypoints.
- `test_reproducibility.py` (2 tests): Identical generator runs, bitwise identical file exports.
- `test_synthetic_validation.py` (5 tests): Seed constants, config presets, split line allocations, referential validity.
- `test_validation.py` (1 test): System schema and identifier validation.

---

## 7. Dashboard Access Instructions

Start the application:

```bash
python run.py
```

Open your browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### Key Application Routes:
- `/` or `/overview`: Operations executive dashboard & real-time KPIs
- `/sellers`: Seller directory, SLA scorecards, and compliance status
- `/listings`: Catalog SKU management and stock status
- `/orders`: Multi-seller split order view and tracking
- `/fulfillments`: Carrier tracking numbers and delivery milestone scans
- `/disputes`: Claim management and resolution deductions
- `/commissions`: Fee tier schedules, minimum floors, and maximum caps
- `/payouts`: Bi-weekly settlement disbursements and header-to-line itemizations
- `/anomalies`: Anomaly detection engine results across all 5 operational scenarios
- `/reports`: Export manager with download links for all CSV, JSON, and SQL files
- `/api/health`: Health probe endpoint returning database status and latency

---

## 8. Export Directory Structure

All generated export artifacts are saved in `exports/`:

```
seller_operations_system/exports/
├── manifest.json                     # SHA-256 cryptographic checksums & row counts
├── dataset_full.json                 # Comprehensive JSON dataset (FULL preset)
├── dataset_starter.json              # Benchmark JSON dataset (STARTER preset)
├── seed_full.sql                     # Universal SQL DDL & INSERT script (FULL preset)
├── seed_starter.sql                  # Universal SQL DDL & INSERT script (STARTER preset)
├── ground_truth_anomalies.csv        # Ground truth labels (isolated)
├── ground_truth_anomalies.json       # Ground truth labels in JSON
├── detected_anomalies.csv            # Detection engine results (isolated)
├── detected_anomalies.json           # Detection engine results in JSON
├── sellers.csv                       # 2,000 seller accounts
├── product_listings.csv              # 20,000 SKU catalog entries
├── customers.csv                     # 8,000 buyer accounts
├── orders.csv                        # 100,000 customer orders
├── order_lines.csv                   # 195,290 seller-specific order items
├── fulfillments.csv                  # 189,403 carrier package tracking records
├── customer_reviews.csv              # 62,338 post-delivery customer reviews
├── disputes.csv                      # 10,000 dispute claims & resolutions
├── commission_rules.csv              # 6 category fee rate schedules
├── payouts.csv                       # 11,307 settlement disbursement headers
├── payout_lines.csv                  # 339,238 itemized transaction entries
├── anomalies_ground_truth.csv        # Reference ground truth anomalies
├── seller_status_events.csv          # Seller state transition log
├── listing_status_events.csv         # Product catalog status transition log
├── order_status_events.csv           # Order progression milestone events
├── fulfillment_events.csv            # Carrier checkpoint scan events
└── payout_events.csv                 # Disbursement lifecycle events
```

---

## 9. Verification & Integrity Summary

- **Foreign Key Integrity:** 0 violations across 1.9M records (`PRAGMA foreign_key_check`).
- **Primary Key Uniqueness:** 0 duplicates across all 17 tables.
- **Orphan Records:** 0 orphans across all 18 parent-child relational foreign keys.
- **Anomaly Detection Performance:**
  - True Positives (TP): 6
  - False Positives (FP): 0
  - False Negatives (FN): 0
  - Precision: **100.0%**
  - Recall: **100.0%**
  - F1-Score: **1.0000**
- **Financial Reconciliation:** 11,306 payouts reconcile to $0.00 variance; exactly 1 intentional discrepancy flagged (Scenario 5, +$250.00).
- **Deterministic Reproducibility:** 100% bitwise matching export files with seed `20261022`.
