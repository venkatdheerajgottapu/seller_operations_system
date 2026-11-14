# Seller Operations & Payout Intelligence Platform

An enterprise-grade marketplace seller operations, multi-seller order fulfillment, settlement calculation, and financial anomaly intelligence platform built with **Python 3**, **Flask**, **SQLAlchemy**, **Pandas**, **Bootstrap 5**, and **Chart.js**.

---

## 1. Project Overview & Architecture

The **Seller Operations & Payout Intelligence Platform** manages complex multi-seller marketplace operations with financial accuracy and full relational auditability:

- **Multi-Seller Order Allocation:** Automatically splits customer shopping cart orders into seller-specific fulfillment lines with individual tracking numbers, carrier logistics tracking, and independent status transitions.
- **Service Level Agreements (SLA):** Continuously derives seller quality metrics (on-time shipment rate, fulfillment rate, cancellation rate, return rate, dispute rate) directly from actual transaction events.
- **Effective-Dated Commission Engine:** Computes category-based marketplace commission fees with configurable minimum fee floors ($0.50 / $1.00) and maximum fee caps ($150.00).
- **Settlement Mathematical Formula:**
  $$\text{Net Payout} = \text{Gross Sales} - \text{Commission} - \text{Refunds} - \text{Dispute Deductions} - \text{Reserve Holds} + \text{Eligible Adjustments}$$
  Every monetary operation is strictly computed using `DECIMAL(12, 2)` fixed-point arithmetic.
- **Audit & Financial Reconciliation:** Verifies header-to-line integrity so that the sum of signed payout line items equals the header net settlement amount.
- **Independent Anomaly Detection:** Rule-based detection engine monitors 5 business invariants without access to ground truth, achieving **100% precision, 100% recall, and 100% F1-score** across validated benchmark datasets.
- **Cryptographic Export Pipeline:** Generates 17 relational CSVs, isolated ground truth and detected anomaly exports, structured JSON dataset, complete MySQL seed file, and a SHA-256 manifest catalog.

---

## 2. Technology Stack

- **Backend Framework:** Python 3.12+ / 3.14 (Flask 3.1.3, Werkzeug 3.1.8)
- **Database & ORM:** SQLAlchemy 2.1.8 (Pure Python mode, Windows Application Control compliant)
- **Relational Databases:** PostgreSQL 15+, MySQL Server 8.0, and local SQLite fallback
- **Production WSGI Servers:** Gunicorn 22.0+ (Linux/Containers), Waitress 3.0+ (Windows/Local)
- **Data & Testing:** Pandas 3.0.3, Faker 40.54.0, Pytest 9.2.0 (56 automated tests)
- **Frontend & Visualizations:** HTML5, Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Chart.js 4.4.2
- **Containerization & Hosting:** Docker, Docker Compose, Render Blueprint (`render.yaml`)

---

## 3. Environment Variables Reference

All credentials and runtime settings are configured via environment variables or a `.env` file (see `.env.example`):

| Variable | Default Value | Description |
|---|---|---|
| `FLASK_APP` | `run.py` | Application entrypoint script |
| `FLASK_ENV` | `development` | Environment mode (`development`, `testing`, `production`) |
| `FLASK_DEBUG` | `0` (Prod) / `1` (Dev) | Flask debug mode flag |
| `SECRET_KEY` | *(Auto-generated / Set in .env)* | 32-byte cryptographic secret key for session signing |
| `PORT` | `5000` | HTTP port for web server binding |
| `HOST` | `0.0.0.0` (Prod) / `127.0.0.1` | Network interface binding |
| `DATABASE_URL` | *None* | Full database URI (e.g. `postgresql://...` or `mysql+mysqlconnector://...`) |
| `DB_HOST` | `127.0.0.1` | Database server host (used if `DATABASE_URL` is unset) |
| `DB_PORT` | `3306` | Database server port |
| `DB_USER` | `root` | Database username |
| `DB_PASSWORD` | *Empty* | Database password (if empty, defaults to local SQLite) |
| `DB_NAME` | `seller_ops_db` | Database schema name |
| `DB_POOL_SIZE` | `10` | SQLAlchemy engine connection pool size |
| `DB_MAX_OVERFLOW` | `20` | SQLAlchemy engine max overflow connections |
| `SESSION_COOKIE_SECURE` | `true` (Prod) | Enforces HTTPS-only cookies in production |
| `WORKERS` | `4` | Number of Gunicorn worker processes |
| `LOG_LEVEL` | `info` | Logging verbosity (`debug`, `info`, `warning`, `error`) |

---

## 4. Local Setup & Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/venkatdheerajgottapu/seller_operations_system.git
cd seller_operations_system/seller_operations_system
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 4: Configure Local Environment
```bash
# Copy template configuration
cp .env.example .env

# Generate a secure secret key and update SECRET_KEY in .env
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 5. Database Provisioning & Management

The platform supports **PostgreSQL**, **MySQL 8.0**, and **SQLite**:

### 1. Initialize Tables (Safe & Idempotent)
Creates all 17 tables without dropping or altering existing data:
```bash
python database/init_db.py
```

### 2. Verify Database Connection
Inspect dialect, latency, server version, and connectivity:
```bash
python database/init_db.py --check
```

### 3. Seed Initial Dataset (Only If Database is Empty)
Populate database with synthetic deterministic seed `20261022`:
```bash
# Starter Preset (20 sellers, 200 listings, 500 orders, 50 disputes)
python database/init_db.py --seed --preset STARTER

# Medium Preset (200 sellers, 2,000 listings, 10,000 orders, 1,000 disputes)
python database/init_db.py --seed --preset MEDIUM

# Full Preset (2,000 sellers, 20,000 listings, 100,000 orders, 10,000 disputes)
python database/init_db.py --seed --preset FULL
```
> **Safety Invariant:** If the database already contains records, `--seed` automatically skips generation (`[SKIP SEEDING]`) to prevent accidental overwrites or data loss in production.
>
> **Important — Backing Up Before Destructive Reset:**
> If you need to re-seed or switch presets, always create a timestamped backup first:
> ```bash
> python database/backup_restore.py
> ```
> To explicitly overwrite an existing database, pass `--force-seed` (requires explicit operator confirmation):
> ```bash
> python database/init_db.py --seed --preset FULL --force-seed
> ```
> *Warning: `--force-seed` drops all existing schema tables and regenerates data from scratch. Never execute without an existing backup.*

### 4. Backup & Restoration
```bash
# Create point-in-time database snapshot (saved in backups/)
python database/backup_restore.py

# Restore from a backup snapshot
python database/backup_restore.py --restore backups/sqlite_backup_20261113_142500.sqlite
```

---

## 6. Running the Application

### Local Development Mode (Debug Enabled)
```bash
python run.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### Local Production Simulation (Debug Disabled)
```bash
# Windows
$env:FLASK_ENV="production"; python wsgi.py

# Linux / macOS
FLASK_ENV=production python wsgi.py
```

### Run Automated Pytest Suite (56 Passing Tests)
```bash
python -m pytest -v
```

---

## 7. Production Deployment Instructions

### Option A: Render Cloud Deployment (Recommended)
The repository includes a ready-to-deploy `render.yaml` Blueprint:

1. Push your repository to GitHub.
2. Sign in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** &rarr; **Blueprint**.
4. Connect `seller_operations_system` repository.
5. Render reads `render.yaml` and automatically provisions:
   - Web Service with Python 3 environment.
   - Build Command: `pip install -r requirements.txt && python database/init_db.py --seed`
   - Start Command: `gunicorn -c gunicorn.conf.py wsgi:app`
   - Health Check Path: `/api/health`
   - Auto-generated `SECRET_KEY` and managed PostgreSQL database `DATABASE_URL`.
6. Click **Apply** to deploy live.

### Option B: Docker Container Deployment
A multi-stage, non-root hardened `Dockerfile` and `docker-compose.yml` are included:

```bash
# Build and start web application and MySQL 8.0 database
docker compose up -d --build

# View container logs
docker compose logs -f web

# Health check verification
curl -f http://localhost:5000/api/health
```

### Option C: Manual Linux VM / VPS Deployment (Ubuntu / Debian)
```bash
# 1. Install system packages
sudo apt update && sudo apt install -y python3-pip python3-venv nginx

# 2. Clone repository & configure venv
git clone https://github.com/venkatdheerajgottapu/seller_operations_system.git /opt/seller_ops
cd /opt/seller_ops/seller_operations_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Setup environment and database
cp .env.example .env
nano .env  # set FLASK_ENV=production, SECRET_KEY, and DATABASE_URL
python database/init_db.py --seed

# 4. Launch with Gunicorn
gunicorn -c gunicorn.conf.py wsgi:app
```

---

## 8. Health-Check & Monitoring Endpoints

- **JSON Health API:** `GET /api/health`
  - Returns HTTP 200 when healthy, HTTP 503 when attention is required.
  - Diagnostics include Python version, OS architecture, package versions, database engine dialect, latency in milliseconds, and server version.
- **Visual Health Dashboard:** `GET /health`
  - Responsive Bootstrap interface displaying real-time system metrics.

---

## 9. Security Posture & Hardening

- **Zero Hardcoded Secrets:** `SECRET_KEY` and database passwords must be supplied via environment variables; default dev keys emit runtime warnings in production.
- **OWASP SQL Injection Protection:** 100% parameterized queries via SQLAlchemy ORM.
- **Path Traversal Defense:** File downloads on `/exports/download/<filename>` use `werkzeug.utils.secure_filename()` with strict directory confinement.
- **Production Data Protection:** Destructive synthetic data regeneration is explicitly blocked when `FLASK_ENV=production`.
- **Masked Error Reporting:** Unhandled 500 errors generate unique incident UUIDs; raw tracebacks are routed strictly to encrypted rotating server logs (`logs/app.log`).
- **Security Response Headers:**
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: SAMEORIGIN`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy` restricting script and style origins.
- **Container Least Privilege:** Docker container runs as unprivileged system user `appuser` (UID 1000).

---

## 10. Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| `DeprecationWarning: datetime.utcnow()` | Python 3.12+ deprecation | Code uses modern naive UTC helper `utcnow()` from `database.connection`. |
| `WinError 10013` socket forbidden | Windows network sandbox restriction | Use in-process `app.test_client()` for tests or execute with network access outside sandbox. |
| `SQLAlchemy cython DLL block` | Windows Application Control policy | Handled automatically: pure Python SQLAlchemy mode active with zero compilation errors. |
| `UNIQUE constraint failed: rule_id` | Duplicate seeding attempt | Handled automatically: `init_db.py` checks existing records before seeding. |
| `Database connection notice: SQLite fallback active` | MySQL server not running or credentials omitted | Expected behavior: system seamlessly operates using high-performance local SQLite database. |

---

## 11. Known Limitations

1. **In-Memory SQLite Pooling:** In-memory SQLite (`:memory:`) does not support multi-threaded connection pooling. Use file-based SQLite, MySQL, or PostgreSQL for concurrent environments.
2. **Dynamic Data Regeneration in Production:** For data safety, the `/reports/regenerate` web endpoint is intentionally disabled in production mode. Seeding in production should only be executed via `python database/init_db.py --seed` during initial deployment.
3. **Synchronous Export Generation:** Generating very large datasets (`FULL` preset: 100,000 orders) executes synchronously. For multi-million order benchmarks, run generation via background CLI or worker queue.

---

## 12. Verification & Validation Status

- **Automated Test Suite:** 56 passing tests (44 unit/integration + 8 production config & security tests + 4 comprehensive financial reconciliation tests).
- **FULL Preset Generation:** Successfully generated and verified (2,000 sellers, 20,000 listings, 100,000 orders, 10,000 disputes; 1,908,020 total records across 17 tables).
- **Referential Integrity:** 0 foreign key violations verified via SQLite engine (`PRAGMA foreign_key_check`), 0 duplicate primary keys, 0 orphan records.
- **Anomaly Detection:** All 5 labelled ground-truth scenarios verified with independent rule detection.
- **Deployment Status:** Architecture, WSGI (Gunicorn / Waitress), Docker, and security headers configured and validated.
