# Seller Operations & Payout Intelligence System

An end-to-end, enterprise-grade marketplace monitoring, settlement calculation, multi-seller fulfillment, and financial anomaly intelligence platform built with Python, Flask, SQLAlchemy, Pandas, Faker, Bootstrap 5, and Chart.js.

---

## 1. System Architecture & Capabilities

- **Multi-Seller Order Allocation:** Automatically splits customer shopping cart orders into seller-specific fulfillment lines with individual tracking numbers and independent lifecycle events.
- **Service Level Agreements (SLA):** Continuously calculates and monitors on-time shipment rate, fulfillment rate, cancellation rate, return rate, and customer dispute rate per seller.
- **Effective-Dated Commission Engine:** Computes marketplace commissions based on listing categories with minimum transaction fee floors and maximum caps.
- **Financial Settlement Formula:**
  $$\text{Net Payout} = \text{Gross Sales} - \text{Commission} - \text{Refunds} - \text{Dispute Deductions} - \text{Reserve Holds} + \text{Eligible Adjustments}$$
  Every monetary operation uses high-precision `DECIMAL(12, 2)` arithmetic.
- **Header-to-Line Item Reconciliation:** Automatically checks that the sum of signed payout line items equals the header net settlement amount.
- **Independent Anomaly Detection:** An anomaly detection rule engine evaluates database invariants without access to ground truth.

---

## 2. Windows Environment & Security Compliance

- **Windows Application Control Compliance:** Never calls `pip.exe` directly; all installations and executions use module invocations (`python -m pip`, `python -m pytest`).
- **Pure Python SQLAlchemy Fallback:** Disabled unapproved user-space compiled Cython DLLs (`*.pyd`) in `%APPDATA%`, letting SQLAlchemy operate in 100% compliant pure Python mode without triggering security policy alerts.
- **Database Driver:** Supports MySQL Server 8.0 via `mysql-connector-python` with automatic SQLite local fallback (`seller_ops_db.sqlite`) enabled when MySQL credentials are not supplied.

---

## 3. Database Schema (17 Tables)

### 11 Core Entities
1. `sellers`: Profile, status, quality metrics (SLA), reserve rates (e.g. 10%).
2. `product_listings`: Category, SKU, stock quantity, price, publication status.
3. `customers`: Contact information, delivery addresses.
4. `orders`: Order dates, multi-seller lines, gross totals, payment status.
5. `order_lines`: Multi-seller item splitting, unit prices, commissions.
6. `fulfillments`: Tracking numbers, carrier (FedEx, UPS, DHL, BlueDart), shipping delays.
7. `customer_reviews`: 1-5 star ratings, feedback reviews.
8. `disputes`: Chargebacks, claim amounts, clawback deductions, resolution dates.
9. `commission_rules`: Category fee schedules, effective date intervals, min/max caps.
10. `payouts`: Settlement batches, gross, deductions, reserves, net payout, reconciliation state.
11. `payout_lines`: Itemized line ledger (`SALE`, `COMMISSION`, `DISPUTE`, `RESERVE_HOLD`, `REFUND`).

### 5 Event History Tables
1. `seller_status_events`: Status transitions and administrative review notes.
2. `listing_status_events`: Publication, modification, and delisting history.
3. `order_status_events`: Checkout to delivery state transitions.
4. `fulfillment_events`: Logistics waypoints (`LABEL_CREATED`, `PICKUP`, `IN_TRANSIT`, `DELIVERED`).
5. `payout_events`: Settlement batch scheduling and disbursement history.

### 1 Anomaly Table
- `anomalies`: Records both ground-truth benchmark violations and independent runtime rule detections.

---

## 4. Deterministic ID Conventions

Deterministic, zero-padded identifier conventions:
- **Seller:** `SELL-000001`
- **Product Listing:** `LIST-SELL-000001-000001`
- **Customer:** `CUST-000001`
- **Order:** `ORD-2026-000001`
- **Order Line:** `ORD-2026-000001-01`
- **Fulfillment:** `FUL-ORD-2026-000001-01`
- **Dispute:** `DSP-2026-000001`
- **Payout:** `PAYOUT-2026-000001`
- **Payout Line:** `PAYLINE-000001-001`

---

## 5. Anomaly Detection & Ground-Truth Benchmark

The system benchmarks 5 anomaly scenarios using strict set evaluation without information leakage:

| Scenario | Invariant Rule | Ground Truth | Detected | Recall | Precision | F1-Score |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **1. Payout Before Delivery** | Paid payout contains unfulfilled / in-transit line | 2 | 2 | 100% | 100% | **1.00** |
| **2. Duplicate Commission** | Order line charged > 1 commission deduction | 1 | 1 | 100% | 100% | **1.00** |
| **3. Suspended Seller Active Listing** | Suspended seller maintains active catalog listing | 1 | 1 | 100% | 100% | **1.00** |
| **4. Dispute Not Deducted** | Settled customer-favor dispute missing payout debit | 1 | 1 | 100% | 100% | **1.00** |
| **5. Financial Discrepancy** | Payout header net != sum of payout lines | 1 | 3* | 100% | 33% | **0.50** |

*\*Note: In Scenario 1, injecting premature lines without header synchronization naturally triggers Scenario 5 reconciliation failure, which is the mathematically expected behavior.*

**Overall Benchmark:** Recall: **100%**, F1-Score: **85.7%**, Accuracy: **99.8%**.

---

## 6. Frontend Dashboard & Views

1. **Executive Overview (`/`):** 11 live KPI cards and 4 Chart.js charts (Order Lifecycle, Category Gross Sales, Carrier Delays, Monthly Payout Trends).
2. **Seller Management (`/sellers`):** Status filtering, on-time shipment rate, fulfillment rate, dispute rate, ratings, suspend/activate actions, SLA recalculation.
3. **Product Listings (`/listings`):** Catalog search, category filter, stock level badges, price.
4. **Order Management (`/orders`):** Order status filtering, multi-seller split indicators.
5. **Order Detail (`/orders/<id>`):** Multi-seller order line allocation, seller breakdown, timeline audit.
6. **Fulfillment Monitoring (`/fulfillments`):** Carrier tracking numbers, delivery dates, delay badges (+X days delay).
7. **Dispute Management (`/disputes`):** Customer claims, resolution workflow (Refund / Dismiss).
8. **Commission Management (`/commissions`):** Effective-dated category schedules and duplicate audit rules.
9. **Payout Management (`/payouts`):** Settlement batches, gross, deductions, reserves, net payout, reconciliation status.
10. **Payout Audit (`/payouts/<id>`):** Mathematical formula decomposition, sum of lines vs header, itemized line items.
11. **Anomaly Monitoring (`/anomalies`):** Confusion matrix (TP, FP, FN, TN), Precision/Recall/F1, scenario breakdown, detected violations log.
12. **Reports & Exports (`/reports`):** Download links for all 12 CSVs, JSON dataset, SQL seed file, and trigger data generator with `STARTER`, `MEDIUM`, or `FULL` presets.
13. **System Health (`/health`):** Real-time runtime diagnostics and database connection health.

---

## 7. How to Run

### Execute Test Suite (18 Unit, Integration, & Schema Tests)
```powershell
python -m pytest
```

### Start Web Application Server
```powershell
python run.py
```
Open your browser to: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

### Re-seed Synthetic Dataset from Command Line
```powershell
python -c "
from database.connection import init_db, get_engine, Base
from data_generator.generator import SyntheticDataGenerator
from data_generator.exporter import export_dataset

engine = get_engine()
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

gen = SyntheticDataGenerator()
gen.generate('STARTER') # Or 'MEDIUM' / 'FULL'
gen.save_to_db()
export_dataset(gen, prefix='starter')
"
```
