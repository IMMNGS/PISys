# Patient Information System — Full Codebase Documentation

> **Version:** 1.0.0  
> **Last Updated:** February 10, 2026  
> **Stack:** Python 3 / Flask / SQLAlchemy (backend) · TypeScript / React / Vite (frontend) · MySQL (database)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure](#2-project-structure)
3. [Getting Started](#3-getting-started)
4. [Configuration](#4-configuration)
5. [Database Schema](#5-database-schema)
6. [Backend — Python / Flask](#6-backend--python--flask)
   - 6.1 [Entry Point — run.py](#61-entry-point--runpy)
   - 6.2 [Application Factory — backend/app.py](#62-application-factory--backendapppy)
   - 6.3 [Configuration — backend/config.py](#63-configuration--backendconfigpy)
   - 6.4 [Models — backend/models.py](#64-models--backendmodelspy)
   - 6.5 [Seed Script — backend/seed.py](#65-seed-script--backendseedpy)
   - 6.6 [Mock Data Generator — backend/generate_mock_data.py](#66-mock-data-generator--backendgenerate_mock_datapy)
   - 6.7 [Route Registration — backend/routes/\_\_init\_\_.py](#67-route-registration--backendroutesinitpy)
   - 6.8 [Shared Helpers — backend/routes/helpers.py](#68-shared-helpers--backendrouteshelperspy)
   - 6.9 [HPO Term Routes — backend/routes/hpo_terms.py](#69-hpo-term-routes--backendrouteshpo_termspy)
   - 6.10 [Patient Routes — backend/routes/patients.py](#610-patient-routes--backendroutespatientspy)
   - 6.11 [Singleton Routes — backend/routes/singletons.py](#611-singleton-routes--backendroutessingletonspy)
   - 6.12 [Trio Routes — backend/routes/trios.py](#612-trio-routes--backendroutestriospy)
   - 6.13 [VCF Routes — backend/routes/vcf.py](#613-vcf-routes--backendroutesvcfpy)
   - 6.14 [Report Routes — backend/routes/reports.py](#614-report-routes--backendroutesreportspy)
7. [Frontend — TypeScript / React / Vite](#7-frontend--typescript--react--vite)
   - 7.1 [Build & Dev Configuration](#71-build--dev-configuration)
   - 7.2 [Application Entry — main.tsx & App.tsx](#72-application-entry--maintsx--apptsx)
   - 7.3 [Type Definitions — types/index.ts](#73-type-definitions--typesindexts)
   - 7.4 [API Client — api/client.ts](#74-api-client--apiclientts)
   - 7.5 [Components](#75-components)
   - 7.6 [Pages](#76-pages)
8. [API Reference](#8-api-reference)
9. [Data Directory](#9-data-directory)
10. [Environment Variables Reference](#10-environment-variables-reference)
11. [Deployment Notes](#11-deployment-notes)

---

## 1. Architecture Overview

The Patient Information System is a full-stack web application for managing patient records, genetic variant findings (singleton and trio analyses), VCF file uploads, HPO (Human Phenotype Ontology) term management, and clinical report generation in `.docx` format.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser (React SPA)                       │
│  React 18 + TypeScript + React Router + Vite                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │  HTTP (JSON + FormData)
                             │  /api/*
┌────────────────────────────▼─────────────────────────────────────┐
│                     Flask Application Server                     │
│  - Serves REST API under /api                                    │
│  - Serves built React SPA for all other routes                   │
│  - CORS enabled for Vite dev server                              │
│  Blueprints: hpo_terms, patients, singletons, trios, vcf,reports │
└────────┬──────────────────────────────┬──────────────────────────┘
         │  SQLAlchemy (PyMySQL)        │  Filesystem I/O
         ▼                              ▼
┌─────────────────┐          ┌─────────────────────┐
│    MySQL 8.0+   │          │   data/vcf/<lab>/    │
│  patient_db     │          │  VCF file storage    │
│                 │          │  (local or NFS/S3)   │
└─────────────────┘          └─────────────────────┘
```

**Key design decisions:**

- **Application factory pattern** (`create_app()`) for testability and flexible configuration.
- **Single database** (`patient_db`) holding all tables — patients, HPO terms, singletons, trios, VCF metadata, and the many-to-many join table.
- **File storage** for VCF files is on disk under a configurable `DATA_DIR`/`VCF_DIR`, enabling future migration to network-mounted or cloud-fuse storage.
- **SPA fallback**: In production, Flask serves the built React app from `frontend/dist/`. During development, Vite's dev server on port 3000 proxies `/api` requests to Flask on port 5001.

---

## 2. Project Structure

```
HA/
├── run.py                        # Application entry-point
├── setup.sh                      # One-command full setup script
├── requirements.txt              # Python dependencies
├── README.md                     # Project README
├── DOCUMENTATION.md              # This file
│
├── backend/                      # Flask backend package
│   ├── __init__.py               # Package marker
│   ├── app.py                    # Flask app factory + SPA serving
│   ├── config.py                 # Configuration class (env-var driven)
│   ├── models.py                 # SQLAlchemy ORM models
│   ├── seed.py                   # DB seeder: HPO CSV + 20 mock patients
│   ├── generate_mock_data.py     # Bulk 1,000-patient generation script
│   └── routes/                   # API route blueprints
│       ├── __init__.py           # Blueprint registration
│       ├── helpers.py            # Shared utilities & field constants
│       ├── hpo_terms.py          # HPO term endpoints
│       ├── patients.py           # Patient CRUD + XLSX import + HPO assignment
│       ├── singletons.py         # Singleton variant CRUD + XLSX import
│       ├── trios.py              # Trio variant CRUD + XLSX import
│       ├── vcf.py                # VCF file upload, list, delete
│       └── reports.py            # Report preview + .docx generation
│
├── data/                         # Data directory (configurable via DATA_DIR)
│   ├── all_hpo_terms.csv         # ~19,500 HPO terms seed file
│   └── vcf/                      # Patient VCF files (one subfolder per lab_number)
│
├── frontend/                     # React + TypeScript SPA (Vite)
│   ├── index.html                # HTML entry-point
│   ├── package.json              # npm dependencies & scripts
│   ├── tsconfig.json             # TypeScript configuration
│   ├── vite.config.ts            # Vite dev server + build config
│   └── src/
│       ├── main.tsx              # React DOM mount point
│       ├── App.tsx               # Router setup with all page routes
│       ├── index.css             # Global CSS styles
│       ├── api/
│       │   └── client.ts         # Typed HTTP client for all API endpoints
│       ├── types/
│       │   └── index.ts          # TypeScript interfaces for domain entities
│       ├── components/
│       │   ├── Navbar.tsx        # Top navigation bar
│       │   ├── DropdownSelect.tsx    # Multi-select dropdown with search
│       │   └── SearchableSelect.tsx  # Single-select combobox with server pagination
│       └── pages/
│           ├── Home.tsx          # Landing page with feature cards
│           ├── SelectPatients.tsx    # Patient table + analysis code export
│           ├── PatientDetail.tsx     # Full patient detail view
│           ├── Upload.tsx           # File upload + patient import
│           ├── Report.tsx           # Report preview & .docx generation
│           └── ManageHpo.tsx        # HPO term assignment + browsing
```

---

## 3. Getting Started

### Prerequisites

| Dependency | Minimum Version |
| ---------- | --------------- |
| Python     | 3.9+            |
| Node.js    | 18+             |
| MySQL      | 8.0+            |

### Automated Setup

```bash
chmod +x setup.sh
./setup.sh
```

The `setup.sh` script performs the following steps:

1. **Prerequisite check** — verifies Python 3, pip, Node.js, npm, and MySQL CLI are available.
2. **Virtual environment** — creates/activates a `.venv` directory.
3. **Python dependencies** — `pip install -r requirements.txt`.
4. **MySQL database** — creates the `patient_db` database (or the database named by `MYSQL_DB`).
5. **Data directories** — creates `data/` and `data/vcf/`.
6. **Frontend build** — runs `npm install && npm run build` in `frontend/`.
7. **Database seeding** — seeds HPO terms from CSV and creates 20 mock patients with singleton findings.

After setup, start the server:

```bash
python run.py
```

Open [http://localhost:5001](http://localhost:5001).

### Manual Setup

```bash
# 1. Python dependencies
pip install -r requirements.txt

# 2. Create MySQL database
mysql -u root -e "CREATE DATABASE IF NOT EXISTS patient_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 3. Build frontend
cd frontend && npm install && npm run build && cd ..

# 4. Seed database
python -m backend.seed

# 5. (Optional) Generate 1,000 mock patients for load testing
python -m backend.generate_mock_data

# 6. Run
python run.py
```

### Development Mode

Run the Flask backend and Vite dev server separately for hot-reloading:

```bash
# Terminal 1: Backend
python run.py          # Flask on port 5001

# Terminal 2: Frontend
cd frontend && npm run dev    # Vite on port 3000, proxies /api → 5001
```

---

## 4. Configuration

All configuration is centralized in `backend/config.py` via the `Config` class. Every setting can be overridden with environment variables.

| Setting              | Env Var          | Default                               | Description                                    |
| -------------------- | ---------------- | ------------------------------------- | ---------------------------------------------- |
| `SECRET_KEY`         | `SECRET_KEY`     | `dev-secret-key-change-in-production` | Flask secret key                               |
| `MYSQL_USER`         | `MYSQL_USER`     | `root`                                | MySQL username                                 |
| `MYSQL_PASSWORD`     | `MYSQL_PASSWORD` | (empty)                               | MySQL password                                 |
| `MYSQL_HOST`         | `MYSQL_HOST`     | `localhost`                           | MySQL hostname                                 |
| `MYSQL_PORT`         | `MYSQL_PORT`     | `3306`                                | MySQL port                                     |
| `MYSQL_DB`           | `MYSQL_DB`       | `patient_db`                          | Database name                                  |
| `DATA_DIR`           | `DATA_DIR`       | `<project_root>/data`                 | Root data directory for VCF files and CSV data |
| `MAX_CONTENT_LENGTH` | `MAX_UPLOAD_MB`  | `5000` MB                             | Maximum upload file size                       |

The `SQLALCHEMY_DATABASE_URI` is constructed automatically from the MySQL settings:

```
mysql+pymysql://<user>:<password>@<host>:<port>/<db>
```

`VCF_DIR` is derived as `DATA_DIR/vcf/`.

---

## 5. Database Schema

All tables reside in a single MySQL database (`patient_db` by default). SQLAlchemy ORM models define the schema and handle migrations via `db.create_all()`.

### Entity Relationship Diagram

```
┌─────────────────┐       ┌────────────────────┐       ┌─────────────────┐
│   hpo_terms     │       │   patient_hpo      │       │    patients     │
│─────────────────│       │────────────────────│       │─────────────────│
│ id (PK)         │◄──────│ hpo_term_id (FK)   │──────►│ id (PK)         │
│ hpo_id (UQ)     │       │ patient_id (FK)    │       │ lab_number (UQ) │
│ term_name       │       │ date_added         │       │ name            │
│ definition      │       │ id (PK)            │       │ hkid, dob, sex  │
│ synonyms        │       └────────────────────┘       │ age, age_unit   │
└─────────────────┘                                    │ ethnicity       │
                                                       │ case_history    │
                    ┌─────────────────────┐            │ type_of_test    │
                    │    singleton        │            │ type_of_findings│
                    │─────────────────────│            │ findings_summary│
                    │ id (PK)             │            │ report_date     │
                    │ patient_id (FK) ────┼───────────►│ specimen_*      │
                    │ gene_names          │            │ ngs_batch/tat   │
                    │ hgvs_c, hgvs_p      │            │ request_dr      │
                    │ chr_pos, ref_alt    │            │ remark          │
                    │ zygosity            │            │ created_at      │
                    │ classification      │            └─────────────────┘
                    │ inheritance         │                    │
                    │ ...                 │                    │
                    └─────────────────────┘                    │
                                                               │
                    ┌─────────────────────┐                    │
                    │       trio          │                    │
                    │─────────────────────│                    │
                    │ id (PK)             │                    │
                    │ patient_id (FK) ────┼────────────────────┘
                    │ (same fields as     │                    │
                    │  singleton)         │                    │
                    └─────────────────────┘                    │
                                                               │
                    ┌─────────────────────┐                    │
                    │    vcf_files        │                    │
                    │─────────────────────│                    │
                    │ id (PK)             │                    │
                    │ patient_id (FK) ────┼────────────────────┘
                    │ filename            │
                    │ relative_path       │
                    │ file_size           │
                    │ uploaded_at         │
                    └─────────────────────┘
```

### Table Details

#### `patients`

Primary entity representing a patient record.

| Column               | Type           | Constraints           | Description                                      |
| -------------------- | -------------- | --------------------- | ------------------------------------------------ |
| `id`                 | `INTEGER`      | PK, auto-increment    | Internal surrogate key                           |
| `lab_number`         | `VARCHAR(100)` | UNIQUE, NOT NULL, IDX | Unique lab identifier (e.g., `LAB-001`)          |
| `im_lab_number`      | `VARCHAR(100)` | nullable              | Internal medicine lab reference                  |
| `name`               | `VARCHAR(200)` | nullable              | Patient full name                                |
| `hkid`               | `VARCHAR(50)`  | nullable              | Hong Kong Identity Card number                   |
| `dob`                | `DATE`         | nullable              | Date of birth                                    |
| `sex`                | `VARCHAR(20)`  | nullable              | "Male" / "Female"                                |
| `age`                | `INTEGER`      | nullable              | Patient age (numeric)                            |
| `age_unit`           | `VARCHAR(20)`  | nullable              | "Years" / "Months" / "Days"                      |
| `ethnicity`          | `VARCHAR(100)` | nullable              | Patient ethnicity                                |
| `specimen_collected` | `DATE`         | nullable              | Date specimen was collected                      |
| `specimen_arrived`   | `DATE`         | nullable              | Date specimen arrived at lab                     |
| `case_history`       | `TEXT`         | nullable              | Clinical case history description                |
| `type_of_test`       | `VARCHAR(200)` | nullable              | Test type (e.g., "WES", "BRCA Panel")            |
| `type_of_findings`   | `VARCHAR(200)` | nullable              | "Positive" / "VUS" / "Negative" / "Inconclusive" |
| `findings_summary`   | `TEXT`         | nullable              | Summary of test findings                         |
| `ngs_batch`          | `VARCHAR(100)` | nullable              | NGS batch identifier                             |
| `ngs_tat`            | `VARCHAR(100)` | nullable              | Turnaround time                                  |
| `ngs_tat_final`      | `VARCHAR(100)` | nullable              | Final turnaround time                            |
| `request_dr`         | `VARCHAR(200)` | nullable              | Requesting physician                             |
| `remark`             | `TEXT`         | nullable              | Free-text remarks                                |
| `report_date`        | `DATE`         | nullable              | Date the report was issued                       |
| `created_at`         | `DATETIME`     | default `utcnow`      | Row creation timestamp                           |

**Relationships:**

- One-to-many → `singleton` (cascade delete)
- One-to-many → `trio` (cascade delete)
- One-to-many → `vcf_files` (cascade delete)
- Many-to-many → `hpo_terms` (via `patient_hpo`)

#### `hpo_terms`

Reference table for Human Phenotype Ontology terms.

| Column       | Type           | Constraints           | Description                         |
| ------------ | -------------- | --------------------- | ----------------------------------- |
| `id`         | `INTEGER`      | PK, auto-increment    | Surrogate key                       |
| `hpo_id`     | `VARCHAR(20)`  | UNIQUE, NOT NULL, IDX | HPO identifier (e.g., `HP:0001250`) |
| `term_name`  | `VARCHAR(500)` | NOT NULL              | Human-readable term name            |
| `definition` | `TEXT`         | nullable              | Term definition                     |
| `synonyms`   | `TEXT`         | nullable              | Comma-separated synonyms            |

#### `patient_hpo` (association table)

Many-to-many join between `patients` and `hpo_terms`.

| Column        | Type       | Constraints                 | Description                      |
| ------------- | ---------- | --------------------------- | -------------------------------- |
| `id`          | `INTEGER`  | PK                          | Surrogate key                    |
| `patient_id`  | `INTEGER`  | FK → patients.id, NOT NULL  | Patient reference                |
| `hpo_term_id` | `INTEGER`  | FK → hpo_terms.id, NOT NULL | HPO term reference               |
| `date_added`  | `DATETIME` | default `utcnow`            | When the association was created |

**Constraint:** `UNIQUE(patient_id, hpo_term_id)` prevents duplicate assignments.

#### `singleton`

Stores singleton variant findings linked to patients.

| Column                  | Type           | Constraints               | Description                                |
| ----------------------- | -------------- | ------------------------- | ------------------------------------------ |
| `id`                    | `INTEGER`      | PK, auto-increment        | Surrogate key                              |
| `patient_id`            | `INTEGER`      | FK → patients.id, IDX     | Owning patient                             |
| `reportable_variant`    | `TEXT`         | nullable                  | Variant designation                        |
| `chr_pos`               | `VARCHAR(200)` | nullable                  | Chromosomal position (e.g., `7:117559590`) |
| `ref_alt`               | `VARCHAR(500)` | nullable                  | Reference/alternate alleles                |
| `igv_review`            | `BOOLEAN`      | nullable, default `False` | Whether IGV review was performed           |
| `second_review_comment` | `TEXT`         | nullable                  | Reviewer comment                           |
| `gene_names`            | `TEXT`         | nullable                  | Gene name(s) (e.g., `CFTR`)                |
| `hgvs_c`                | `VARCHAR(500)` | nullable                  | HGVS coding DNA notation                   |
| `hgvs_p`                | `VARCHAR(500)` | nullable                  | HGVS protein notation                      |
| `exon_number`           | `VARCHAR(100)` | nullable                  | Exon/intron number                         |
| `zygosity`              | `VARCHAR(50)`  | nullable                  | Zygosity state                             |
| `inheritance`           | `VARCHAR(100)` | nullable                  | Inheritance pattern                        |
| `inherited_from`        | `VARCHAR(100)` | nullable                  | Parent of origin                           |
| `classification`        | `VARCHAR(200)` | nullable                  | ACMG classification                        |
| `omim_id`               | `VARCHAR(50)`  | nullable                  | OMIM disease ID                            |
| `rsid`                  | `VARCHAR(50)`  | nullable                  | dbSNP rsID                                 |
| `title`                 | `VARCHAR(500)` | nullable                  | Disease name / phenotype title             |
| `omimid`                | `VARCHAR(50)`  | nullable                  | OMIM gene ID                               |
| `gene_region_combined`  | `TEXT`         | nullable                  | Gene region (Exonic/Intronic/etc.)         |
| `created_at`            | `DATETIME`     | default `utcnow`          | Row creation timestamp                     |

#### `trio`

Identical schema to `singleton` — stores trio analysis variant findings. Same columns and types.

#### `vcf_files`

Metadata for uploaded VCF files. Actual files reside on disk.

| Column          | Type            | Constraints           | Description              |
| --------------- | --------------- | --------------------- | ------------------------ |
| `id`            | `INTEGER`       | PK, auto-increment    | Surrogate key            |
| `patient_id`    | `INTEGER`       | FK → patients.id, IDX | Owning patient           |
| `filename`      | `VARCHAR(500)`  | NOT NULL              | Sanitized filename       |
| `relative_path` | `VARCHAR(1000)` | NOT NULL              | Path relative to VCF_DIR |
| `file_size`     | `BIGINT`        | nullable              | File size in bytes       |
| `uploaded_at`   | `DATETIME`      | default `utcnow`      | Upload timestamp         |

---

## 6. Backend — Python / Flask

### 6.1 Entry Point — `run.py`

```python
from backend.app import create_app
app = create_app()
if __name__ == "__main__":
    app.run(debug=True, port=5001)
```

- Imports and calls the application factory.
- Runs the Flask development server on **port 5001** with debug mode enabled.
- In production, use a WSGI server (Gunicorn, uWSGI) pointed at `create_app()`.

### 6.2 Application Factory — `backend/app.py`

**Function: `create_app(config_class=Config) → Flask`**

Creates and configures the Flask application instance.

**Responsibilities:**

1. **Creates Flask app** with `static_folder` pointed at `frontend/dist/` for serving the built SPA.
2. **Loads configuration** from the `Config` class.
3. **Enables CORS** for `/api/*` endpoints (allows the Vite dev server on port 3000).
4. **Initializes SQLAlchemy** via `db.init_app(app)`.
5. **Registers all API blueprints** under the `/api` URL prefix.
6. **Sets up SPA fallback routing**: any non-API route serves `index.html` from the built frontend; if the frontend isn't built, returns a helpful message.
7. **Ensures the MySQL database exists** (creates it if missing via raw PyMySQL connection).
8. **Creates all database tables** via `db.create_all()`.

**Function: `_ensure_databases(config_class)`**

Connects directly to MySQL (without specifying a database) and executes:

```sql
CREATE DATABASE IF NOT EXISTS `<db_name>` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
```

### 6.3 Configuration — `backend/config.py`

**Class: `Config`**

A plain Python class whose class attributes constitute the application configuration. All values are read from environment variables with sensible defaults for local development.

Key computed attributes:

- `SQLALCHEMY_DATABASE_URI` — assembled from the MySQL connection parameters.
- `VCF_DIR` — `os.path.join(DATA_DIR, "vcf")`.
- `MAX_CONTENT_LENGTH` — controls Flask's maximum upload body size (default 5 GB).

### 6.4 Models — `backend/models.py`

Defines the SQLAlchemy ORM models and the shared `db` instance.

**`db = SQLAlchemy()`** — the extension instance, initialized with the app in the factory.

**Models:**

| Model       | Table Name  | Description                |
| ----------- | ----------- | -------------------------- |
| `HPOTerm`   | `hpo_terms` | HPO reference data         |
| `Patient`   | `patients`  | Patient records            |
| `Singleton` | `singleton` | Singleton variant findings |
| `Trio`      | `trio`      | Trio variant findings      |
| `VcfFile`   | `vcf_files` | VCF file metadata          |

**Association Table: `patient_hpo`** — many-to-many join between patients and HPO terms with a `date_added` timestamp and a unique constraint on `(patient_id, hpo_term_id)`.

Every model has a **`to_dict()`** method that returns a JSON-serializable dictionary. The `Patient.to_dict()` method accepts flags to control inclusion of nested collections:

```python
patient.to_dict(
    include_hpo=True,          # Include HPO terms array
    include_singletons=False,  # Include singleton findings
    include_trios=False,       # Include trio findings
    include_vcf_files=False,   # Include VCF file metadata
)
```

### 6.5 Seed Script — `backend/seed.py`

**Usage:** `python -m backend.seed`

Seeds the database with initial data:

1. **`seed_hpo_terms(csv_path)`** — reads `data/all_hpo_terms.csv` and bulk-inserts HPO terms that don't already exist. Expects columns: `hpo_id`, `term_name`, `definition`, `synonyms`.

2. **`seed_patients()`** — creates 20 predefined mock patients with:
   - Realistic clinical data (case histories, test types, findings).
   - One singleton variant finding per patient.
   - 1–4 random HPO term assignments per patient.
   - Skips patients whose `lab_number` already exists.

**Helper functions:**

- `random_date(start_year, end_year)` — generates a random date in the given year range.
- `random_dob(age, age_unit)` — derives a plausible date of birth from age/unit.

### 6.6 Mock Data Generator — `backend/generate_mock_data.py`

**Usage:** `python -m backend.generate_mock_data`

Generates **1,000 mock patients** (lab numbers `LAB-0100` through `LAB-1099`) for load testing. Safe to run multiple times — duplicates are skipped.

**For each patient creates:**

- 1–3 singleton variant findings.
- 0–2 trio variant findings (for ~40% of patients).
- 1–5 random HPO term assignments.

**Data pools include:**

- 170+ male first names, 170+ female first names, 200+ last names.
- 40+ realistic gene variants with HGVS notation, OMIM IDs, chromosomal positions.
- Weighted distributions for ethnicities, test types, finding types, classifications, zygosities.

**Key functions:**

- `generate_patient(idx)` — generates a randomized patient dict.
- `generate_variant(patient_id)` — generates a randomized variant dict for either singleton or trio use.
- `random_hkid()` — generates a plausible Hong Kong ID card number.
- **Batch processing** — commits in batches of 100 for performance.

### 6.7 Route Registration — `backend/routes/__init__.py`

Defines the `ALL_BLUEPRINTS` list and the `register_blueprints(app, url_prefix="/api")` function that iterates through all blueprints and registers them with the given prefix.

**Blueprints registered:**

1. `hpo_bp` — HPO term endpoints
2. `patients_bp` — Patient endpoints
3. `singletons_bp` — Singleton variant endpoints
4. `trios_bp` — Trio variant endpoints
5. `vcf_bp` — VCF file endpoints
6. `reports_bp` — Report endpoints

### 6.8 Shared Helpers — `backend/routes/helpers.py`

**Functions:**

- **`_patient_to_dict(patient, ...)`** — wrapper around `Patient.to_dict()` that forwards inclusion flags.
- **`_parse_xlsx_rows(file_storage)`** — reads an `.xlsx` file from a Flask `FileStorage` object using `openpyxl`, normalizes header names (lowercase, spaces → underscores), and returns a list of dicts.

**Constants:**

- `PATIENT_FIELDS` — tuple of all patient column names accepted during create/update.
- `SINGLETON_FIELDS` — tuple of all singleton variant column names.
- `TRIO_FIELDS` — tuple of all trio variant column names.
- `DATE_FIELDS` — set of field names that should be parsed as dates (`dob`, `report_date`, `specimen_collected`, `specimen_arrived`).

### 6.9 HPO Term Routes — `backend/routes/hpo_terms.py`

**Blueprint:** `hpo_bp` (name: `"hpo_terms"`)

| Method | Endpoint                   | Handler             | Description                                       |
| ------ | -------------------------- | ------------------- | ------------------------------------------------- |
| POST   | `/api/hpo_terms/refresh`   | `refresh_hpo_terms` | Pull latest terms from `pyhpo` library and upsert |
| GET    | `/api/hpo_terms`           | `get_hpo_terms`     | Search/paginate HPO terms                         |
| GET    | `/api/hpo_terms/<term_id>` | `get_hpo_term`      | Get a single HPO term by ID                       |

**`POST /api/hpo_terms/refresh`**

- Imports `pyhpo.Ontology`, iterates all terms, and upserts (adds new, updates changed).
- Returns `{ message, added, updated }`.
- Returns 500 if `pyhpo` is not installed.

**`GET /api/hpo_terms`**  
Query params: `search` (filters by HPO ID, term name, or synonyms), `page` (default 1), `per_page` (default 50).

- Returns `{ items: [...], total, page, pages }`.

### 6.10 Patient Routes — `backend/routes/patients.py`

**Blueprint:** `patients_bp` (name: `"patients"`)

#### CRUD Endpoints

| Method | Endpoint                     | Handler               | Description                              |
| ------ | ---------------------------- | --------------------- | ---------------------------------------- |
| GET    | `/api/patients`              | `get_patients`        | List all patients (with optional search) |
| GET    | `/api/patients/options`      | `get_patient_options` | Lightweight paginated patient picker     |
| GET    | `/api/patients/list`         | `get_patient_list`    | Paginated table view with column filters |
| GET    | `/api/patients/<patient_id>` | `get_patient`         | Single patient with all nested data      |
| POST   | `/api/patients`              | `create_patient`      | Create a new patient (JSON body)         |
| PUT    | `/api/patients/<patient_id>` | `update_patient`      | Update a patient (JSON body)             |
| DELETE | `/api/patients/<patient_id>` | `delete_patient`      | Delete a patient and all associations    |

**`GET /api/patients`**

- `search` query param filters across `lab_number`, `name`, `type_of_test`, `type_of_findings`, `request_dr`.
- Returns full patient data with HPO, singletons, trios, and VCF files.

**`GET /api/patients/options`**

- Returns `{ items: [{id, lab_number, name}], total }`.
- Query params: `search`, `limit` (default 20), `offset` (default 0).
- Designed for dropdown/combobox population with server-side pagination.

**`GET /api/patients/list`**

- Returns `{ items: [...], total }` — patients serialized without nested data.
- Supports per-column filters: `lab_number`, `im_lab_number`, `name`, `sex`, `age`, `type_of_test`.
- Query params: `limit` (default 20), `offset` (default 0).

#### Bulk Import

**`POST /api/patients/upload`**

- Accepts multipart/form-data with a `file` field containing an `.xlsx` file.
- Each row in the spreadsheet becomes a patient. `lab_number` column is required.
- Duplicate lab numbers are **skipped** (not updated) and reported.
- Returns `{ message, added, skipped: [...] }` with HTTP 201.

#### HPO Assignment

| Method | Endpoint                                         | Handler                   | Description                       |
| ------ | ------------------------------------------------ | ------------------------- | --------------------------------- |
| GET    | `/api/patients/<patient_id>/hpo_terms`           | `get_patient_hpo_terms`   | List HPO terms for a patient      |
| POST   | `/api/patients/assign_hpo`                       | `assign_hpo_to_patients`  | Bulk-assign HPO terms to patients |
| DELETE | `/api/patients/<patient_id>/hpo_terms/<term_id>` | `remove_hpo_from_patient` | Remove an HPO term from a patient |

**`POST /api/patients/assign_hpo`**

- Body: `{ "patient_ids": [1, 2], "hpo_term_ids": [5, 10] }`
- Assigns each specified HPO term to each specified patient (skips existing assignments).

#### Analysis Selection

**`POST /api/patients/selected`**

- Body: `{ "patient_ids": [1, 2, 3] }`
- Returns full patient records (with all nested data) for the specified IDs.
- Used by the frontend's "Extract Selected" feature.

### 6.11 Singleton Routes — `backend/routes/singletons.py`

**Blueprint:** `singletons_bp` (name: `"singletons"`)

| Method | Endpoint                                      | Handler                  | Description                       |
| ------ | --------------------------------------------- | ------------------------ | --------------------------------- |
| GET    | `/api/patients/<patient_id>/singletons`       | `get_patient_singletons` | List all singletons for a patient |
| POST   | `/api/patients/<patient_id>/singletons`       | `create_singleton`       | Create a singleton (JSON body)    |
| GET    | `/api/singletons/<singleton_id>`              | `get_singleton`          | Get a singleton by ID             |
| PUT    | `/api/singletons/<singleton_id>`              | `update_singleton`       | Update a singleton (JSON body)    |
| DELETE | `/api/singletons/<singleton_id>`              | `delete_singleton`       | Delete a singleton                |
| POST   | `/api/patients/<patient_id>/upload/singleton` | `upload_singleton_xlsx`  | Import singletons from XLSX       |

**XLSX Import:** Column headers should match model fields (case-insensitive, spaces → underscores). Unrecognized columns are silently ignored. All rows create new records.

### 6.12 Trio Routes — `backend/routes/trios.py`

**Blueprint:** `trios_bp` (name: `"trios"`)

| Method | Endpoint                                 | Handler             | Description                  |
| ------ | ---------------------------------------- | ------------------- | ---------------------------- |
| GET    | `/api/patients/<patient_id>/trios`       | `get_patient_trios` | List all trios for a patient |
| POST   | `/api/patients/<patient_id>/trios`       | `create_trio`       | Create a trio (JSON body)    |
| PUT    | `/api/trios/<trio_id>`                   | `update_trio`       | Update a trio (JSON body)    |
| DELETE | `/api/trios/<trio_id>`                   | `delete_trio`       | Delete a trio                |
| POST   | `/api/patients/<patient_id>/upload/trio` | `upload_trio_xlsx`  | Import trios from XLSX       |

Mirrors the singleton routes with identical structure and XLSX import behavior.

### 6.13 VCF Routes — `backend/routes/vcf.py`

**Blueprint:** `vcf_bp` (name: `"vcf"`)

| Method | Endpoint                         | Handler           | Description                  |
| ------ | -------------------------------- | ----------------- | ---------------------------- |
| GET    | `/api/patients/<patient_id>/vcf` | `list_vcf_files`  | List VCF files for a patient |
| POST   | `/api/patients/<patient_id>/vcf` | `upload_vcf`      | Upload a VCF file            |
| DELETE | `/api/vcf_files/<vcf_id>`        | `delete_vcf_file` | Delete a VCF file            |

**Allowed extensions:** `.vcf`, `.vcf.gz`, `.bcf`

**Upload flow:**

1. Validates file type against `ALLOWED_VCF_EXTENSIONS`.
2. Creates directory `VCF_DIR/<lab_number>/` if needed.
3. Saves file with `werkzeug.utils.secure_filename`.
4. Records metadata (filename, relative path, file size) in `vcf_files` table.

**Delete flow:**

1. Removes the file from disk (if it exists).
2. Deletes the database record.

**Storage note:** `VCF_DIR` can point to a local directory or a network mount (NFS, SSHFS, S3-Fuse). To use remote storage, set the `DATA_DIR` environment variable.

### 6.14 Report Routes — `backend/routes/reports.py`

**Blueprint:** `reports_bp` (name: `"reports"`)

| Method | Endpoint               | Handler           | Description                          |
| ------ | ---------------------- | ----------------- | ------------------------------------ |
| POST   | `/api/report/preview`  | `preview_report`  | Get report data for frontend preview |
| POST   | `/api/report/generate` | `generate_report` | Generate and download .docx report   |

**`POST /api/report/preview`**

Body: `{ "lab_number": "LAB-001", "test_type": "singleton" | "trio" }`

Returns:

```json
{
  "patient": { ... },
  "variants": [ ... ],
  "defaults": {
    "test_process": "...",
    "disclaimer": "...",
    "references": "..."
  }
}
```

The `defaults` provide pre-filled text for the test process description, disclaimer, and references sections.

**`POST /api/report/generate`**

Body:

```json
{
  "lab_number": "LAB-001",
  "test_type": "singleton",
  "conclusion": "Free-text conclusion...",
  "test_process": "Editable test process...",
  "disclaimer": "Editable disclaimer...",
  "references": "Editable references..."
}
```

Generates a `.docx` document using `python-docx` with the following sections:

1. **Patient Identity** — Name, Sex/Age, HKID.
2. **Testing Information** — Case history, type of test, specimen collected date.
3. **Result Table** — Columns: Gene Name/OMIM, HGVS transcript/variant, Exon, Zygosity, Inheritance, Parent Origin, Classification, Position REF/ALT, Assembly (GRCh38/hg38), SNP Identifier, Phenotype.
4. **Conclusion** — User-provided text.
5. **Test Process** — Editable description (defaults provided).
6. **Disclaimer** — Editable legal text.
7. **References** — Editable citations.

Returns the `.docx` as a downloadable attachment named `report_<lab_number>.docx`.

**Default text constants:**

- `DEFAULT_TEST_PROCESS` — describes the sequencing methodology (panel, pipeline, reference genome).
- `DEFAULT_DISCLAIMER` — describes test limitations (SNVs, indels, structural variants).
- `DEFAULT_REFERENCES` — default citation(s).

---

## 7. Frontend — TypeScript / React / Vite

### 7.1 Build & Dev Configuration

**`package.json`** — Defines the project as an ES module with these key dependencies:

| Package                | Role                         |
| ---------------------- | ---------------------------- |
| `react` / `react-dom`  | UI framework (v18.3)         |
| `react-router-dom`     | Client-side routing (v6.26)  |
| `vite`                 | Build tool/dev server (v5.4) |
| `typescript`           | Language (v5.5)              |
| `@vitejs/plugin-react` | Vite React plugin            |

**npm scripts:**

- `dev` — starts Vite dev server (port 3000).
- `build` — compiles TypeScript then builds for production into `dist/`.
- `preview` — serves the production build locally.

**`vite.config.ts`:**

- Dev server on port 3000.
- Proxies `/api` requests to `http://localhost:5001` (Flask backend).
- Production build outputs to `frontend/dist/`.

### 7.2 Application Entry — `main.tsx` & `App.tsx`

**`main.tsx`** — mounts the React app into `#root` with `React.StrictMode`.

**`App.tsx`** — defines the application's route structure using `react-router-dom`:

| Route           | Component        | Description                         |
| --------------- | ---------------- | ----------------------------------- |
| `/`             | `Home`           | Landing page with feature cards     |
| `/patients/:id` | `PatientDetail`  | Individual patient detail view      |
| `/select`       | `SelectPatients` | Patient table with filters & export |
| `/upload`       | `Upload`         | File upload & patient import        |
| `/report`       | `Report`         | Clinical report generation          |
| `/manage-hpo`   | `ManageHpo`      | HPO term management & assignment    |

Wraps all routes with `Navbar` and a `<footer>`.

### 7.3 Type Definitions — `types/index.ts`

Defines TypeScript interfaces mirroring the backend's JSON serialization:

| Interface       | Description                                                                                |
| --------------- | ------------------------------------------------------------------------------------------ |
| `HPOTerm`       | HPO term with id, hpo_id, term_name, definition, synonyms                                  |
| `SingletonInfo` | Singleton variant finding with all genetic fields                                          |
| `TrioInfo`      | Trio variant finding (identical structure to SingletonInfo)                                |
| `VcfFileInfo`   | VCF file metadata (filename, size, upload time)                                            |
| `PatientInfo`   | Full patient record with optional nested arrays of HPO terms, singletons, trios, VCF files |
| `HPOTermPage`   | Paginated HPO term response (`items`, `total`, `page`, `pages`)                            |

### 7.4 API Client — `api/client.ts`

A typed HTTP client module that provides functions for every backend endpoint. All functions use a shared `json<T>()` helper that calls `fetch()`, checks for errors, and returns typed JSON.

**Helper function:**

```typescript
async function json<T>(url: string, init?: RequestInit): Promise<T>;
```

**Exported interfaces:**

- `PatientOption` — lightweight patient reference (`id`, `lab_number`, `name`).
- `PaginatedOptions<T>` — `{ items: T[], total: number }`.
- `PatientListFilters` — column filter parameters.
- `ReportPreview` — preview data structure.

**Exported functions by domain:**

| Category    | Function                | HTTP Method | Endpoint                              |
| ----------- | ----------------------- | ----------- | ------------------------------------- |
| HPO Terms   | `fetchHPOTerms`         | GET         | `/api/hpo_terms`                      |
|             | `refreshHPOTerms`       | POST        | `/api/hpo_terms/refresh`              |
| Patients    | `fetchPatients`         | GET         | `/api/patients`                       |
|             | `fetchPatientOptions`   | GET         | `/api/patients/options`               |
|             | `fetchPatientList`      | GET         | `/api/patients/list`                  |
|             | `fetchPatient`          | GET         | `/api/patients/:id`                   |
|             | `fetchSelectedPatients` | POST        | `/api/patients/selected`              |
|             | `uploadPatientsXlsx`    | POST        | `/api/patients/upload`                |
| HPO assign  | `assignHPO`             | POST        | `/api/patients/assign_hpo`            |
|             | `removeHPO`             | DELETE      | `/api/patients/:id/hpo_terms/:termId` |
| Singletons  | `fetchSingletons`       | GET         | `/api/patients/:id/singletons`        |
|             | `createSingleton`       | POST        | `/api/patients/:id/singletons`        |
|             | `updateSingleton`       | PUT         | `/api/singletons/:id`                 |
|             | `deleteSingleton`       | DELETE      | `/api/singletons/:id`                 |
| VCF Files   | `fetchVcfFiles`         | GET         | `/api/patients/:id/vcf`               |
|             | `uploadVcfFile`         | POST        | `/api/patients/:id/vcf`               |
|             | `deleteVcfFile`         | DELETE      | `/api/vcf_files/:id`                  |
| XLSX Import | `uploadSingletonXlsx`   | POST        | `/api/patients/:id/upload/singleton`  |
|             | `uploadTrioXlsx`        | POST        | `/api/patients/:id/upload/trio`       |
| Reports     | `fetchReportPreview`    | POST        | `/api/report/preview`                 |
|             | `downloadReport`        | POST        | `/api/report/generate`                |

**File uploads** use `FormData` and handle the response as a blob (for report download) or JSON.

**Report download** creates a temporary `<a>` element to trigger a browser download of the `.docx` file.

### 7.5 Components

#### `Navbar.tsx`

Top navigation bar using `react-router-dom`'s `NavLink` for active-state highlighting.

**Links:** Home, Patients, Upload, Report, Manage HPO Terms.

#### `DropdownSelect.tsx`

A multi-select dropdown component with built-in search and progressive loading.

**Props:**

| Prop          | Type                   | Description                                |
| ------------- | ---------------------- | ------------------------------------------ |
| `items`       | `DropdownItem[]`       | All available items (`{ id, label }`)      |
| `placeholder` | `string`               | Trigger button text when nothing selected  |
| `selectedIds` | `Set<number>`          | Currently selected item IDs                |
| `onToggle`    | `(id: number) => void` | Callback when an item is checked/unchecked |
| `pageSize`    | `number` (default 20)  | How many items to show initially           |

**Features:**

- Search filtering on label text.
- "Load more" button for progressive disclosure (shows `pageSize` items at a time).
- Closes on outside click.
- Auto-focuses search input when opened.

#### `SearchableSelect.tsx`

A single-select combobox with server-side paginated search.

**Props:**

| Prop           | Type                                              | Description                    |
| -------------- | ------------------------------------------------- | ------------------------------ |
| `value`        | `string`                                          | Current selected value         |
| `onChange`     | `(value: string) => void`                         | Selection callback             |
| `fetchOptions` | `(search, limit, offset) => Promise<FetchResult>` | Server fetch function          |
| `placeholder`  | `string`                                          | Placeholder text               |
| `debounceMs`   | `number` (default 250)                            | Search debounce delay          |
| `itemLabel`    | `string`                                          | Label for "Load more X" button |
| `pageSize`     | `number` (default 20)                             | Initial fetch size             |
| `loadMoreSize` | `number` (default 100)                            | Batch size for "load more"     |

**Features:**

- Debounced server-side search.
- "Load more" pagination.
- Clear button (×) to reset selection.
- Options fetched lazily on first open.

### 7.6 Pages

#### `Home.tsx`

Landing page with four feature cards:

| Card                 | Links to      | Description                                        |
| -------------------- | ------------- | -------------------------------------------------- |
| **Patients**         | `/select`     | Filter and select patients for analysis            |
| **Upload**           | `/upload`     | Upload VCF files, singletons, trios, patient lists |
| **Report**           | `/report`     | Generate clinical .docx reports                    |
| **Manage HPO Terms** | `/manage-hpo` | Search and assign HPO terms to patients            |

#### `SelectPatients.tsx`

Patient table with filtering, selection, and analysis code export.

**Features:**

- **Paginated table** loaded from `/api/patients/list` with server-side column filters (lab number, IM lab number, name, sex, age, test type).
- **Debounced filter inputs** (300ms).
- **Checkbox selection** with select-all toggle.
- **"Load more" pagination** — loads additional patients in batches of 100.
- **"Extract Selected" action** — fetches full data for selected patients via `/api/patients/selected`.
- **Code export panel** — after extraction, displays ready-to-use code snippets for:
  - **Python** (using `requests` + `pandas`)
  - **R** (using `httr2` + `jsonlite`)
  - **cURL** (REST commands)
  - **SQL** (direct MySQL queries)
- All snippets dynamically include the selected patient IDs and the current server URL.
- Copy-to-clipboard button for each snippet.
- Collapsible summary table of selected patients with counts of singletons, trios, VCF files, and HPO terms.

#### `PatientDetail.tsx`

Full detail view for a single patient, accessed via `/patients/:id`.

**Layout (two-column):**

| Left Column                | Right Column                              |
| -------------------------- | ----------------------------------------- |
| Patient Demographics table | Associated HPO Terms (with remove button) |
| Clinical Information table | Singleton Findings (card per variant)     |
| Report / NGS Info table    |                                           |

**Actions:**

- Remove individual HPO terms with confirmation.
- "Back to list" link.

#### `Upload.tsx`

File upload and patient import page.

**Sections:**

1. **Import Patients from Excel** — Bulk-import patients from `.xlsx` via `/api/patients/upload`. Displays required (`lab_number`) and optional columns.

2. **Select Patient** — Uses `SearchableSelect` with server-side pagination from `/api/patients/options`. Displays patient as `LAB-XXX — Name`.

3. **Upload File** (shown after patient selection) — radio buttons to choose upload type:
   - **VCF File** (`.vcf`, `.vcf.gz`, `.bcf`) → `/api/patients/:id/vcf`
   - **Singleton Variants** (`.xlsx`) → `/api/patients/:id/upload/singleton`
   - **Trio Variants** (`.xlsx`) → `/api/patients/:id/upload/trio`

4. **VCF Files List** (shown when a patient has VCF files) — table with filename, size (human-readable), upload date, and delete button.

**Helper:** `formatBytes(bytes)` — converts byte counts to human-readable format (B, KB, MB, GB).

#### `Report.tsx`

Clinical report generation with preview and editable sections.

**Workflow:**

1. **Select Lab Number** — uses `SearchableSelect` to pick a lab number with server-side search.
2. **Choose Test Type** — radio: Singleton or Trio.
3. **Load Patient Data** — calls `/api/report/preview` to fetch patient info, variants, and default text.
4. **Preview** — displays:
   - Patient information card (name, sex/age, HKID).
   - Testing information card (case history, test type, specimen collected).
   - Variant result table matching the `.docx` output format.
   - Editable text areas for: Conclusion, Test Process, Disclaimer, References.
5. **Download Report** — calls `/api/report/generate` which returns a `.docx` blob. The blob is converted to a download link automatically.

#### `ManageHpo.tsx`

HPO term management and patient assignment page.

**Sections:**

1. **Side-by-side dropdowns** (two-column layout):
   - **Left: HPO Terms** — `DropdownSelect` listing all HPO terms (`fetchHPOTerms` with large page size). Selected terms shown as removable tags.
   - **Right: Patients** — `DropdownSelect` listing all patients. Selected patients shown as removable tags.

2. **Assign button** — bulk-assigns all selected HPO terms to all selected patients via `/api/patients/assign_hpo`.

3. **Refresh HPO Terms** — button that calls `/api/hpo_terms/refresh` to pull latest terms from the `pyhpo` library. Shows progress message.

4. **Browse HPO Terms** — searchable paginated table of all HPO terms:
   - Search by HPO ID, term name, or synonyms (300ms debounce).
   - Server-side pagination with page navigation controls.
   - Columns: HPO ID, Term Name, Definition (truncated), Synonyms (truncated).

---

## 8. API Reference

### Quick Reference

All endpoints are prefixed with `/api`. Responses are JSON unless otherwise noted.

#### HPO Terms

```
GET    /api/hpo_terms                      → { items, total, page, pages }
GET    /api/hpo_terms/:id                  → HPOTerm
POST   /api/hpo_terms/refresh              → { message, added, updated }
```

#### Patients

```
GET    /api/patients                        → PatientInfo[]
GET    /api/patients/options                → { items: [{id, lab_number, name}], total }
GET    /api/patients/list                   → { items: PatientInfo[], total }
GET    /api/patients/:id                    → PatientInfo (full)
POST   /api/patients                        → PatientInfo (201)
PUT    /api/patients/:id                    → PatientInfo
DELETE /api/patients/:id                    → { message }
POST   /api/patients/upload                 → { message, added, skipped } (201)
POST   /api/patients/selected               → PatientInfo[] (full)
```

#### Patient HPO Terms

```
GET    /api/patients/:id/hpo_terms          → HPOTerm[]
POST   /api/patients/assign_hpo             → { message }
DELETE /api/patients/:id/hpo_terms/:termId  → { message }
```

#### Singleton Variants

```
GET    /api/patients/:id/singletons         → SingletonInfo[]
POST   /api/patients/:id/singletons         → SingletonInfo (201)
GET    /api/singletons/:id                  → SingletonInfo
PUT    /api/singletons/:id                  → SingletonInfo
DELETE /api/singletons/:id                  → { message }
POST   /api/patients/:id/upload/singleton   → { message, count } (201)
```

#### Trio Variants

```
GET    /api/patients/:id/trios              → TrioInfo[]
POST   /api/patients/:id/trios              → TrioInfo (201)
PUT    /api/trios/:id                       → TrioInfo
DELETE /api/trios/:id                       → { message }
POST   /api/patients/:id/upload/trio        → { message, count } (201)
```

#### VCF Files

```
GET    /api/patients/:id/vcf                → VcfFileInfo[]
POST   /api/patients/:id/vcf                → VcfFileInfo (201)
DELETE /api/vcf_files/:id                   → { message }
```

#### Reports

```
POST   /api/report/preview                  → { patient, variants, defaults }
POST   /api/report/generate                 → .docx file (binary download)
```

---

## 9. Data Directory

The `data/` directory is the default location for persistent data files:

```
data/
├── all_hpo_terms.csv         # ~19,500 HPO terms (CSV seed source)
│                              # Columns: hpo_id, term_name, definition, synonyms
└── vcf/                      # VCF file storage
    └── <lab_number>/         # Per-patient subdirectory
        └── *.vcf / *.vcf.gz / *.bcf
```

The entire `data/` directory can be relocated by setting the `DATA_DIR` environment variable. This enables:

- **NFS mounts** for shared lab storage.
- **SSHFS** for remote server access.
- **S3-Fuse** (s3fs, goofys) for cloud storage.

---

## 10. Environment Variables Reference

| Variable         | Default               | Used In     | Description                         |
| ---------------- | --------------------- | ----------- | ----------------------------------- |
| `SECRET_KEY`     | `dev-secret-key-...`  | `config.py` | Flask session secret key            |
| `MYSQL_USER`     | `root`                | `config.py` | MySQL username                      |
| `MYSQL_PASSWORD` | (empty)               | `config.py` | MySQL password                      |
| `MYSQL_HOST`     | `localhost`           | `config.py` | MySQL host                          |
| `MYSQL_PORT`     | `3306`                | `config.py` | MySQL port                          |
| `MYSQL_DB`       | `patient_db`          | `config.py` | MySQL database name                 |
| `DATA_DIR`       | `<project_root>/data` | `config.py` | Root directory for VCF & data files |
| `MAX_UPLOAD_MB`  | `5000`                | `config.py` | Maximum upload size in megabytes    |

---

## 11. Deployment Notes

### Production Checklist

1. **Set `SECRET_KEY`** to a strong random value.
2. **Set `MYSQL_PASSWORD`** and use a non-root MySQL user.
3. **Build the frontend**: `cd frontend && npm ci && npm run build`.
4. **Use a WSGI server** (Gunicorn, uWSGI) instead of Flask's dev server:
   ```bash
   gunicorn "backend.app:create_app()" -b 0.0.0.0:5000 -w 4
   ```
5. **Disable debug mode** — don't pass `debug=True` in production.
6. **Configure `MAX_UPLOAD_MB`** appropriately for expected VCF file sizes.
7. **Set `DATA_DIR`** to a backed-up, high-availability storage location.
8. **Set up MySQL backups** for the `patient_db` database.
9. **Use HTTPS** via a reverse proxy (nginx, Caddy).
10. **Consider disabling CORS** or restricting origins in production.

### Remote Access

The system supports access from remote devices on the same network. The frontend's "Extract Selected" feature generates code snippets that detect the current server URL. For remote access:

- Replace `localhost` with the server's IP address or hostname.
- Ensure port 5001 (or your configured port) is accessible through firewalls.

### Python Dependencies

| Package            | Purpose                                        |
| ------------------ | ---------------------------------------------- |
| `flask`            | Web framework                                  |
| `flask-sqlalchemy` | ORM integration                                |
| `flask-cors`       | Cross-origin resource sharing                  |
| `pymysql`          | MySQL database driver                          |
| `cryptography`     | Required by PyMySQL for authentication         |
| `pandas`           | Data manipulation (used in seed scripts)       |
| `pyhpo`            | Human Phenotype Ontology library (HPO refresh) |
| `openpyxl`         | Excel file reading/writing (.xlsx)             |
| `python-docx`      | Word document generation (.docx reports)       |
