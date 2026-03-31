# Patient Information System — Full Codebase Documentation

> **Version:** 1.4.0  
> **Last Updated:** March 24, 2026  
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
   - 6.5 [Route Registration — backend/routes/\_\_init\_\_.py](#65-route-registration--backendroutesinitpy)
   - 6.6 [Shared Helpers — backend/routes/helpers.py](#66-shared-helpers--backendrouteshelperspy)
   - 6.7 [HPO Term Routes — backend/routes/hpo_terms.py](#67-hpo-term-routes--backendrouteshpo_termspy)
   - 6.8 [Patient Routes — backend/routes/patients.py](#68-patient-routes--backendroutespatientspy)
   - 6.9 [Singleton Routes — backend/routes/singletons.py](#69-singleton-routes--backendroutessingletonspy)
   - 6.10 [Trio Routes — backend/routes/trios.py](#610-trio-routes--backendroutestriospy)
   - 6.11 [VCF Routes — backend/routes/vcf.py](#611-vcf-routes--backendroutesvcfpy)
   - 6.12 [Report Routes — backend/routes/reports.py](#612-report-routes--backendroutesreportspy)
   - 6.13 [Local LLM Routes — backend/routes/local_llm.py](#613-local-llm-routes--backendrouteslocal_llmpy)
   - 6.14 [Local RAG Corpus & Ingestion Scripts](#614-local-rag-corpus--ingestion-scripts)
   - 6.15 [Authentication & Audit — backend/security.py, auth.py, admin.py](#615-authentication--audit--backendsecuritypy-authpy-adminpy)
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
11. [Production Deployment](#11-production-deployment)

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
│              Gunicorn WSGI Server (production)                   │
│  Multi-worker, gthread worker class, 120s timeout                │
│──────────────────────────────────────────────────────────────────│
│                     Flask Application Server                     │
│  - Serves REST API under /api                                    │
│  - Serves built React SPA for all other routes                   │
│  - CORS restricted by origin in production                       │
│  Blueprints: hpo_terms, patients, singletons, trios, vcf,reports │
└────────┬──────────────────────────────┬──────────────────────────┘
         │  SQLAlchemy (PyMySQL)        │  Filesystem I/O
         ▼                              ▼
┌─────────────────┐          ┌───────────────────────────────┐
│    MySQL 8.0+   │          │ data/vcf/<lab>/               │
│  patient_db     │          │ data/variant_uploads/<lab>/   │
│                 │          │ file storage (local or NFS/S3)│
└─────────────────┘          └───────────────────────────────┘
```

**Key design decisions:**

- **Application factory pattern** (`create_app()`) for testability and flexible configuration.
- **Single database** (`patient_db`) holding all tables — patients, HPO terms, singletons, trios, VCF metadata, retained variant upload metadata, and the many-to-many join table.
- **File storage** for VCF files and original singleton/trio upload files is on disk under configurable directories derived from `DATA_DIR`, enabling future migration to network-mounted or cloud-fuse storage.
- **SPA fallback**: In production, Flask serves the built React app from `frontend/dist/`. During development, Vite's dev server on port 3000 proxies `/api` requests to Flask on port 5001.
- **Production-ready**: Gunicorn WSGI server with configurable workers, threads, and timeouts. Environment-based configuration selects `DevelopmentConfig` or `ProductionConfig`.

---

## 2. Project Structure

```
HA/
├── run.py                        # Application entry-point
├── gunicorn.conf.py              # Gunicorn production configuration
├── run.sh                        # Unified setup/start script (setup|development|production)
├── .env.example                  # Environment variable template
├── requirements.txt              # Python dependencies
├── README.md                     # Project README
├── DOCUMENTATION.md              # This file
├── scripts/                      # Setup helpers and local LLM launcher
│   ├── download_qwen_model.sh    # Optional GGUF download helper
│   ├── rag/                      # Local RAG research collection + corpus builders
│   │   ├── fetch_public_research.py  # Europe PMC downloader for raw public research
│   │   └── build_rag_corpus.py       # Chunked JSONL corpus builder
│   └── start_local_llm.py        # llama.cpp launcher or mock OpenAI-compatible server
│
├── backend/                      # Flask backend package
│   ├── __init__.py               # Package marker
│   ├── app.py                    # Flask app factory + SPA serving
│   ├── config.py                 # Configuration class (env-var driven)
│   ├── models.py                 # SQLAlchemy ORM models
│   ├── security.py               # Session auth, password hashing, audit helpers
│   └── routes/                   # API route blueprints
│       ├── __init__.py           # Blueprint registration
│       ├── auth.py               # Login/logout/me/password-change routes
│       ├── admin.py              # Admin user and audit log routes
│       ├── helpers.py            # Shared utilities & field constants
│       ├── hpo_terms.py          # HPO term endpoints
│       ├── local_llm.py          # Local LLM chat + model listing endpoints
│       ├── patients.py           # Patient CRUD + XLSX import + HPO assignment
│       ├── singletons.py         # Singleton variant CRUD + XLSX import
│       ├── trios.py              # Trio variant CRUD + XLSX import
│       ├── vcf.py                # VCF file upload, list, delete
│       └── reports.py            # Report preview + .docx generation
│
├── data/                         # Data directory (configurable via DATA_DIR)
│   ├── all_hpo_terms.csv         # ~19,500 HPO terms (loadable via Manage HPO page)
│   ├── vcf/                      # Patient VCF files (one subfolder per lab_number)
│   ├── variant_uploads/          # Raw singleton/trio XLSX uploads (per patient, per type)
│   ├── rag/                      # Local RAG raw downloads, corpus, and eval sets
│   └── local_ai/                 # Local LLM binaries + GGUF weights (gitignored)
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
│           ├── Assistant.tsx        # Local AI assistant / LLM chat page
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
# First-time setup (creates venv, installs deps, builds frontend)
bash run.sh setup
```

The `run.sh setup` step performs the following steps:

1. **Prerequisite check** — verifies Python 3, pip, Node.js, npm, and MySQL CLI are available.
2. **Virtual environment** — creates/activates a `.venv` directory.
3. **Python dependencies** — `pip install -r requirements.txt`.
4. **MySQL database** — creates the `patient_db` database (or the database named by `MYSQL_DB`) when `mysql` CLI is present.
5. **Data directories** — creates `data/`, `data/vcf/`, and `data/variant_uploads/`.
6. **Frontend build** — runs `npm install && npm run build` in `frontend/`.

After setup, start the server:

```bash
# Development
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

# 4. Load HPO terms (via the app or API)
curl -X POST http://localhost:5000/api/hpo_terms/refresh

# 5. Upload patient data via the Upload page or sample files in data/sample/

# 6. Run (development)
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

### Production Mode

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and MYSQL_PASSWORD

# 2. Generate a secret key
python -c "import secrets; print(secrets.token_hex(32))"

# 3. Start production server (builds frontend and does one-time HPO load)
bash run.sh production
```

Or manually:

```bash
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
cd frontend && npm ci && npm run build && cd ..
gunicorn -c gunicorn.conf.py run:app
```

The production server binds to `0.0.0.0:8000` by default.

---

## 4. Configuration

All configuration is centralized in `backend/config.py` via a class hierarchy (`Config` → `DevelopmentConfig` / `ProductionConfig`). The active config is selected by the `FLASK_ENV` environment variable. Every setting can be overridden with environment variables.

| Setting              | Env Var          | Default                               | Description                                                    |
| -------------------- | ---------------- | ------------------------------------- | -------------------------------------------------------------- |
| `FLASK_ENV`          | `FLASK_ENV`      | `development`                         | Config selection: `development` or `production`                |
| `SECRET_KEY`         | `SECRET_KEY`     | `dev-secret-key-change-in-production` | Flask secret key (**required** in production)                  |
| `MYSQL_USER`         | `MYSQL_USER`     | `root`                                | MySQL username                                                 |
| `MYSQL_PASSWORD`     | `MYSQL_PASSWORD` | (empty)                               | MySQL password                                                 |
| `MYSQL_HOST`         | `MYSQL_HOST`     | `localhost`                           | MySQL hostname                                                 |
| `MYSQL_PORT`         | `MYSQL_PORT`     | `3306`                                | MySQL port                                                     |
| `MYSQL_DB`           | `MYSQL_DB`       | `patient_db`                          | Database name                                                  |
| `DATA_DIR`           | `DATA_DIR`       | `<project_root>/data`                 | Root data directory for VCF, raw variant uploads, and CSV data |
| `VARIANT_UPLOAD_DIR` | (derived)        | `DATA_DIR/variant_uploads`            | Storage directory for original singleton/trio XLSX uploads     |
| `MAX_CONTENT_LENGTH` | `MAX_UPLOAD_MB`  | `5000` MB                             | Maximum upload file size                                       |
| `CORS_ORIGINS`       | `CORS_ORIGINS`   | (none)                                | Comma-separated allowed origins (production)                   |

The `SQLALCHEMY_DATABASE_URI` is constructed automatically from the MySQL settings:

```
mysql+pymysql://<user>:<password>@<host>:<port>/<db>
```

`VCF_DIR` is derived as `DATA_DIR/vcf/`.

`VARIANT_UPLOAD_DIR` is derived as `DATA_DIR/variant_uploads/`.

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
                                                       │ clinical_history│
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
                                                               │
                    ┌─────────────────────┐                    │
                    │  variant_uploads    │                    │
                    │─────────────────────│                    │
                    │ id (PK)             │                    │
                    │ patient_id (FK) ────┼────────────────────┘
                    │ file_type           │
                    │ original_filename   │
                    │ stored_filename     │
                    │ relative_path       │
                    │ file_size           │
                    │ uploaded_at         │
                    └─────────────────────┘
```

### Table Details

#### `patients`

Primary entity representing a patient record.

| Column               | Type           | Constraints           | Description                                             |
| -------------------- | -------------- | --------------------- | ------------------------------------------------------- |
| `id`                 | `INTEGER`      | PK, auto-increment    | Internal surrogate key                                  |
| `lab_number`         | `VARCHAR(100)` | UNIQUE, NOT NULL, IDX | Unique lab identifier (e.g., `LAB-001`)                 |
| `im_lab_number`      | `VARCHAR(100)` | nullable              | Internal medicine lab reference                         |
| `name`               | `VARCHAR(200)` | nullable              | Patient full name                                       |
| `hkid`               | `VARCHAR(50)`  | nullable              | Hong Kong Identity Card number                          |
| `dob`                | `DATE`         | nullable              | Date of birth                                           |
| `sex`                | `VARCHAR(20)`  | nullable              | "Male" / "Female"                                       |
| `age`                | `INTEGER`      | nullable              | Patient age (numeric)                                   |
| `age_unit`           | `VARCHAR(20)`  | nullable              | "Years" / "Months" / "Days"                             |
| `ethnicity`          | `VARCHAR(100)` | nullable              | Patient ethnicity                                       |
| `specimen_collected` | `DATE`         | nullable              | Date specimen was collected                             |
| `specimen_arrived`   | `DATE`         | nullable              | Date specimen arrived at lab                            |
| `clinical_history`   | `TEXT`         | nullable              | Clinical history description (DB column `case_history`) |
| `type_of_test`       | `VARCHAR(200)` | nullable              | Test type (e.g., "WES", "BRCA Panel")                   |
| `type_of_findings`   | `VARCHAR(200)` | nullable              | "Positive" / "VUS" / "Negative" / "Inconclusive"        |
| `findings_summary`   | `TEXT`         | nullable              | Summary of test findings                                |
| `ngs_batch`          | `VARCHAR(100)` | nullable              | NGS batch identifier                                    |
| `ngs_tat`            | `VARCHAR(100)` | nullable              | Turnaround time                                         |
| `ngs_tat_final`      | `VARCHAR(100)` | nullable              | Final turnaround time                                   |
| `request_dr`         | `VARCHAR(200)` | nullable              | Requesting physician                                    |
| `remark`             | `TEXT`         | nullable              | Free-text remarks                                       |
| `report_date`        | `DATE`         | nullable              | Date the report was issued                              |
| `created_at`         | `DATETIME`     | default `utcnow`      | Row creation timestamp                                  |

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
import os
from backend.app import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
```

- Reads `FLASK_ENV` environment variable to select the configuration (`development` or `production`).
- Calls the application factory with the config name.
- When run directly (`python run.py`), starts the Flask development server on **port 5001** with debug mode.
- In production, Gunicorn imports `app` from this module: `gunicorn -c gunicorn.conf.py run:app`.

### 6.2 Application Factory — `backend/app.py`

**Function: `create_app(config_name="development") → Flask`**

Creates and configures the Flask application instance.

**Arguments:**

- `config_name` — one of `"development"`, `"production"`, or `"default"`. Selects the corresponding config class from `backend/config.py`.

**Responsibilities:**

1. **Creates Flask app** with `static_folder` pointed at `frontend/dist/` for serving the built SPA.
2. **Loads configuration** from the selected config class.
3. **Runs config-specific initialization** — e.g., `ProductionConfig.init_app()` validates that `SECRET_KEY` is set.
4. **Configures logging** — structured logging with timestamps in production.
5. **Enables CORS** — allows all origins in development; restricts to `CORS_ORIGINS` in production.
6. **Initializes SQLAlchemy** via `db.init_app(app)`.
7. **Registers all API blueprints** under the `/api` URL prefix.
8. **Sets up SPA fallback routing**: any non-API route serves `index.html` from the built frontend.
9. **Ensures the MySQL database exists** (creates it if missing via raw PyMySQL connection).
10. **Creates all database tables** via `db.create_all()`.

**Function: `_ensure_databases(config_class)`**

Connects directly to MySQL (without specifying a database) and executes:

```sql
CREATE DATABASE IF NOT EXISTS `<db_name>` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
```

### 6.3 Configuration — `backend/config.py`

**Class hierarchy:**

- `Config` — Base class with shared defaults. All values read from environment variables.
- `DevelopmentConfig(Config)` — Sets `DEBUG = True`.
- `ProductionConfig(Config)` — Sets `DEBUG = False`, requires `SECRET_KEY` from env, provides `init_app()` validation.

**Config map:** `config = { "development": DevelopmentConfig, "production": ProductionConfig, "default": DevelopmentConfig }`

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

### 6.5 Route Registration — `backend/routes/__init__.py`

Defines the `ALL_BLUEPRINTS` list and the `register_blueprints(app, url_prefix="/api")` function that iterates through all blueprints and registers them with the given prefix.

**Blueprints registered:**

1. `hpo_bp` — HPO term endpoints
2. `patients_bp` — Patient endpoints
3. `singletons_bp` — Singleton variant endpoints
4. `trios_bp` — Trio variant endpoints
5. `vcf_bp` — VCF file endpoints
6. `reports_bp` — Report endpoints

### 6.6 Shared Helpers — `backend/routes/helpers.py`

**Serialisation:**

- **`_patient_to_dict(patient, ...)`** — wrapper around `Patient.to_dict()` that forwards inclusion flags.

**XLSX Parsing:**

- **`_parse_xlsx_rows(file_storage)`** — reads an `.xlsx` file from a Flask `FileStorage` object using `openpyxl`. Uses `auto_map_columns()` to fuzzy-match Excel column headers to DB field names, then falls back to simple lowercased/underscore-normalised names. Returns a list of dicts.
- **`_parse_variant_xlsx_rows(file_storage)`** — reads a singleton/trio variant XLSX file. Automatically detects whether the header row is row 0 or row 1 (some variant files have a title row). Uses `auto_map_variant_columns()` for column mapping. Returns a list of dicts.

**Validation:**

- **`validate_lab_number(lab_number)`** — validates lab number format against two patterns: `IM###` (3–6 digits) and `XX##XXX` (2-digit + 2-char + 3–6 digits). Returns `True` / `False`.

**Field Metadata:**

- **`get_available_patient_fields()`** — returns a dict mapping every patient DB field name to a human-readable label. Single source of truth for the column-mapping UI.

**Auto-Mapping:**

- **`auto_map_columns(excel_columns, available_fields)`** — maps Excel column names to patient DB field names using two passes: (1) exact / case-insensitive match against a curated variations dict, (2) fuzzy matching via `SequenceMatcher` with a 0.6 threshold. Handles common hospital-specific header names like `"Lab. no."`, `"Sample collection date"`, `"Requesting Dr."`, etc.
- **`auto_map_variant_columns(excel_columns)`** — same approach for variant-specific columns (`"Reportable Variant"`, `"Gene Names"`, `"HGVS c. (Clinically Relevant)"`, etc.).

**Constants:**

- `PATIENT_FIELDS` — tuple of all patient column names accepted during create/update.
- `SINGLETON_FIELDS` — tuple of all singleton variant column names.
- `TRIO_FIELDS` — tuple of all trio variant column names.
- `DATE_FIELDS` — set of field names that should be parsed as dates (`dob`, `report_date`, `specimen_collected`, `specimen_arrived`).
- `_PATIENT_FIELD_VARIATIONS` — internal dict mapping DB field names to lists of known Excel header variations.
- `_VARIANT_FIELD_VARIATIONS` — internal dict mapping variant DB field names to known Excel header variations.

### 6.7 HPO Term Routes — `backend/routes/hpo_terms.py`

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

### 6.8 Patient Routes — `backend/routes/patients.py`

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

#### Update Findings / Report Date

| Method | Endpoint                                              | Handler                           | Description                          |
| ------ | ----------------------------------------------------- | --------------------------------- | ------------------------------------ |
| PUT    | `/api/patients/<patient_id>/findings`                 | `update_findings`                 | Update `type_of_findings` only       |
| PUT    | `/api/patients/<patient_id>/findings_and_report_date` | `update_findings_and_report_date` | Update findings + report_date        |
| GET    | `/api/patients/fields`                                | `get_patient_fields_route`        | Field metadata for column-mapping UI |

**`PUT /api/patients/<patient_id>/findings`**

- Body: `{ "type_of_findings": "C" }`
- Updates only the `type_of_findings` field. Returns fully serialised patient.

**`PUT /api/patients/<patient_id>/findings_and_report_date`**

- Body: `{ "type_of_findings": "C", "report_date": "2025-03-15" }`
- Atomically updates both fields. Returns fully serialised patient.

**`GET /api/patients/fields`**

- Returns `{ success: true, fields: { lab_number: "Lab Number (Required)", ... } }`.
- Used by the frontend to build a dynamic column-mapping UI for XLSX imports.

### 6.9 Singleton Routes — `backend/routes/singletons.py`

**Blueprint:** `singletons_bp` (name: `"singletons"`)

| Method | Endpoint                                      | Handler                 | Description                                          |
| ------ | --------------------------------------------- | ----------------------- | ---------------------------------------------------- |
| GET    | `/api/patients/<patient_id>/singletons`       | `list_singletons`       | List singletons (optional `?reportable_variant=C`)   |
| POST   | `/api/patients/<patient_id>/singletons`       | `create_singleton`      | Create a singleton (JSON body)                       |
| PUT    | `/api/singletons/<singleton_id>`              | `update_singleton`      | Update a singleton (JSON body)                       |
| DELETE | `/api/singletons/<singleton_id>`              | `delete_singleton`      | Delete a singleton                                   |
| POST   | `/api/patients/<patient_id>/upload/singleton` | `upload_singleton_xlsx` | Import singletons from XLSX and retain original file |

**`GET /api/patients/<patient_id>/singletons`**

- Optional query param `reportable_variant` filters by variant type (e.g., `C`, `A`, `I`).
- Returns `SingletonInfo[]` ordered by ID.

**`POST /api/patients/<patient_id>/singletons`**

- Body: JSON with any subset of `SINGLETON_FIELDS` (see helpers).
- The `igv_review` field accepts `true`/`false` strings which are coerced to booleans.
- Returns the created `SingletonInfo` with HTTP 201.

**XLSX Import (`POST .../upload/singleton`):**

- Accepts `.xlsx` / `.xls` files via multipart form.
- Persists the original uploaded file to disk under `VARIANT_UPLOAD_DIR/<lab_number>/singleton/`.
- Stores raw-upload metadata in `variant_uploads`.
- Column headers are fuzzy-matched to DB fields via `auto_map_variant_columns()` — handles names like `"Gene Names"`, `"HGVS c. (Clinically Relevant)"`, `"Second review and comment on reportable variant "`, etc.
- Rows with only `None` / NaN values are skipped.
- Returns `{ message, count }` with HTTP 201.

### 6.10 Trio Routes — `backend/routes/trios.py`

**Blueprint:** `trios_bp` (name: `"trios"`)

| Method | Endpoint                                 | Handler            | Description                                     |
| ------ | ---------------------------------------- | ------------------ | ----------------------------------------------- |
| GET    | `/api/patients/<patient_id>/trios`       | `list_trios`       | List trios (optional `?reportable_variant=C`)   |
| POST   | `/api/patients/<patient_id>/trios`       | `create_trio`      | Create a trio (JSON body)                       |
| PUT    | `/api/trios/<trio_id>`                   | `update_trio`      | Update a trio (JSON body)                       |
| DELETE | `/api/trios/<trio_id>`                   | `delete_trio`      | Delete a trio                                   |
| POST   | `/api/patients/<patient_id>/upload/trio` | `upload_trio_xlsx` | Import trios from XLSX and retain original file |

Mirrors the singleton routes with identical structure and XLSX import behavior. Includes the same `reportable_variant` query filter, fuzzy column mapping, raw file persistence, and upload metadata recording.

### 6.11 VCF Routes — `backend/routes/vcf.py`

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

### 6.12 Report Routes — `backend/routes/reports.py`

**Blueprint:** `reports_bp` (name: `"reports"`)

| Method | Endpoint               | Handler           | Description                          |
| ------ | ---------------------- | ----------------- | ------------------------------------ |
| POST   | `/api/report/preview`  | `report_preview`  | Get report data for frontend preview |
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

The `defaults` provide pre-filled text for the test process description, disclaimer, and references sections. The `variants` array contains singleton or trio records depending on `test_type`.

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

Generates a full clinical `.docx` document using `python-docx` matching the Immunological Disorders SuperPanel report format. The document sections are:

1. **Report Date & Patient Demographics** — Report date, lab numbers, name, HKID, DOB, sex, age, ethnicity, specimen dates.
2. **Separator Line** — visual delimiter.
3. **Clinical Summary** — Specimen type, clinical history, testing requested, test description, summary of results.
4. **Results Table** — Confirmed (C) variant findings in a formatted table: Gene, HGVS c., HGVS p., Exon, Zygosity, Inheritance, Classification, OMIM ID, RSID. Trio reports include an "Inherited From" column.
5. **Additional Findings** (type A) — separate table and interpretation text.
6. **Editable Sections** — Comments, Variant Classification (blank for manual entry).
7. **Appendix** — Incidental findings (type I) with interpretation text.
8. **QC Metrics** — Sequencing Performance Metrics table (Immunological Disorders SuperPanel, 554 genes, 15,798 exons, 2,359,627 bases).
9. **Target Region & Gene List** — Full 554-gene list with coverage footnotes and panel description.
10. **Methods** — Eight underlined subsections: Laboratory process, Bioinformatics and quality control, Interpretation, Variant classification, Databases, Confirmation of sequence alterations, Analytic validation, Assay limitations.
11. **Disclaimers** — Six numbered disclaimers covering legal, clinical, and technical limitations.
12. **Signatures** — Reported By / Signed Out By with named physicians.
13. **End of Report** marker.

Returns the `.docx` as a downloadable attachment named `report_<lab_number>_<im_lab_number>.docx`.

**Key helper functions:**

- `_get_test_description(test_type)` — returns the panel test description blurb, appending "Trio analysis was performed" when `test_type == "trio"`.
- `_get_summary_result(patient)` — generates summary text from the patient's `type_of_findings` and variant data:
  - `C` → counts confirmed variants and names the gene(s).
  - `A` → "No disease-causing variant detected... additional findings included."
  - `I` / `N` → "No disease-causing variant detected."
- `_build_variant_table(doc, variants, include_inherited_from)` — inserts a formatted variant table.
- `_build_qc_table(doc)` — inserts the QC metrics table.
- `create_word_document(patient, test_type)` — orchestrates the full document generation, returns a `BytesIO` buffer.

**Static text constants (module-level):**

- `GENE_LIST` — all 554 panel genes with `*` and `#` annotations.
- `PANEL_DESCRIPTION` — panel scope and limitations.
- `GENE_FOOTNOTE` — explanation of `*` and `#` annotations.
- `METHODS_SECTIONS` — dict of eight method subsection texts.
- `DISCLAIMERS` — list of six disclaimer strings.

### 6.13 Local LLM Routes — `backend/routes/local_llm.py`

**Blueprint:** `local_llm_bp` (name: `"local_llm"`)

| Method | Endpoint                | Handler                 | Description                                  |
| ------ | ----------------------- | ----------------------- | -------------------------------------------- |
| GET    | `/api/local-llm/models` | `list_local_llm_models` | List local GGUF files in the model directory |
| POST   | `/api/local-llm/chat`   | `chat_local_llm`        | Forward chat requests to the loopback server |

**`GET /api/local-llm/models`**

- Reads `LOCAL_AI_MODELS_DIR` from configuration.
- Returns a `models` array with display labels, absolute paths, and a selected default model.
- Falls back to the configured default GGUF path if the directory is empty.

**`POST /api/local-llm/chat`**

Request body:

```json
{
  "model": "qwen3.5-4b-instruct",
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." }
  ],
  "temperature": 0.2,
  "top_p": 0.95,
  "max_tokens": 512
}
```

- Validates that `LOCAL_LLM_BASE_URL` points to a local/loopback host.
- Sends an OpenAI-compatible request to the configured local model server.
- Returns `{ model, reply, raw }` so the frontend can display the model answer and keep the upstream payload for debugging.
- Uses `LOCAL_LLM_TIMEOUT` for the upstream request timeout.

### 6.14 Local RAG Corpus & Ingestion Scripts

The app includes a fully local retrieval corpus under `data/rag/` plus helper scripts for collecting public research that can be used offline after download.

**Directory layout:**

- `data/rag/raw/` — raw downloads from public research sources
- `data/rag/corpus/` — chunked JSONL corpus used for embeddings and retrieval
- `data/rag/eval/` — held-out evaluation questions and answers

**Seed queries:**

- `data/rag/queries.txt` — default search queries focused on rare disease, phenotype, and variant interpretation topics

**Scripts:**

- `scripts/rag/fetch_public_research.py` — downloads public article metadata and abstracts from Europe PMC; can also fetch open-access full text XML when a PMCID exists
- `scripts/rag/build_rag_corpus.py` — converts the raw manifests and text files into a chunked JSONL corpus suitable for embedding and retrieval

**Operational guidance:**

- The download step is the only internet-dependent part; the resulting corpus stays on disk and can be reused fully offline.
- Keep provenance metadata with every record, including PMID/PMCID/DOI, source URL, query, and fetch timestamp.
- Keep evaluation data separate from the retrieval corpus to avoid leakage into benchmarks.

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
| `/assistant`    | `Assistant`      | Local AI assistant / LLM chat       |

Aliases: `/llm` and `/explain` redirect to `/assistant`.

Wraps all routes with `Navbar` and a `<footer>`.

### 7.3 Type Definitions — `types/index.ts`

Defines TypeScript interfaces mirroring the backend's JSON serialization:

| Interface                | Description                                                                                |
| ------------------------ | ------------------------------------------------------------------------------------------ |
| `HPOTerm`                | HPO term with id, hpo_id, term_name, definition, synonyms                                  |
| `SingletonInfo`          | Singleton variant finding with all genetic fields                                          |
| `TrioInfo`               | Trio variant finding (identical structure to SingletonInfo)                                |
| `VcfFileInfo`            | VCF file metadata (filename, size, upload time)                                            |
| `PatientInfo`            | Full patient record with optional nested arrays of HPO terms, singletons, trios, VCF files |
| `HPOTermPage`            | Paginated HPO term response (`items`, `total`, `page`, `pages`)                            |
| `LocalLlmMessage`        | Local assistant chat message (`role`, `content`)                                           |
| `LocalLlmChatResponse`   | Local assistant response (`model`, `reply`)                                                |
| `LocalLlmModelsResponse` | Local assistant model listing (`models`, `selected`)                                       |

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
| Local LLM   | `fetchLocalLlmModels`   | GET         | `/api/local-llm/models`               |
|             | `sendLocalLlmChat`      | POST        | `/api/local-llm/chat`                 |

**File uploads** use `FormData` and handle the response as a blob (for report download) or JSON.

**Report download** creates a temporary `<a>` element to trigger a browser download of the `.docx` file.

### 7.5 Components

#### `Navbar.tsx`

Top navigation bar using `react-router-dom`'s `NavLink` for active-state highlighting.

**Links:** Home, Patients, Upload, Report, Manage HPO Terms, Assistant.

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
| **Assistant**        | `/assistant`  | Local AI chat with the loopback LLM server         |

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

#### `Assistant.tsx`

Local AI assistant page backed by the local LLM proxy.

**Workflow:**

1. **Load models** — fetches available GGUF files from `/api/local-llm/models` and pre-selects the configured default.
2. **Compose message** — sends a system prompt plus user messages to `/api/local-llm/chat`.
3. **Render reply** — shows the model response in a chat-style conversation view.

**Behavior notes:**

- Uses only local/loopback inference endpoints.
- Keeps a minimal medical-assistant style system prompt and avoids external web access.

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
GET    /api/patients/filter_options          → { sex, type_of_test, hpo_terms }
GET    /api/patients/fields                 → { success, fields }
GET    /api/patients/:id                    → PatientInfo (full)
POST   /api/patients                        → PatientInfo (201)
PUT    /api/patients/:id                    → PatientInfo
DELETE /api/patients/:id                    → { message }
POST   /api/patients/upload                 → { message, added, skipped } (201)
POST   /api/patients/selected               → PatientInfo[] (full)
PUT    /api/patients/:id/findings            → PatientInfo
PUT    /api/patients/:id/findings_and_report_date → PatientInfo
```

#### Patient HPO Terms

```
GET    /api/patients/:id/hpo_terms          → HPOTerm[]
POST   /api/patients/assign_hpo             → { message }
DELETE /api/patients/:id/hpo_terms/:termId  → { message }
```

#### Singleton Variants

```
GET    /api/patients/:id/singletons         → SingletonInfo[]  (?reportable_variant=C)
POST   /api/patients/:id/singletons         → SingletonInfo (201)
PUT    /api/singletons/:id                  → SingletonInfo
DELETE /api/singletons/:id                  → { message }
POST   /api/patients/:id/upload/singleton   → { message, count } (201)
```

#### Trio Variants

```
GET    /api/patients/:id/trios              → TrioInfo[]  (?reportable_variant=C)
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

#### Local LLM

```
GET    /api/local-llm/models               → { models, selected }
POST   /api/local-llm/chat                 → { model, reply, raw }
```

#### Authentication and Admin

```
GET    /api/auth/me                        → { authenticated, user }
POST   /api/auth/login                     → { message, user }
POST   /api/auth/logout                    → { message }
POST   /api/auth/change-password           → { message }
GET    /api/admin/users                    → { items }
POST   /api/admin/users                    → { message, user }
GET    /api/admin/audit-logs               → { items, total }
```

### 6.15 Authentication & Audit — `backend/security.py`, `backend/routes/auth.py`, `backend/routes/admin.py`

**Summary:**

- Session-cookie authentication uses Flask's signed session cookie and a `user_id` stored in the session.
- Passwords are hashed with Werkzeug's password hashing helpers.
- Authentication is enabled automatically when at least one `AuthUser` exists; on a fresh database the app seeds a default admin user.
- Administrator endpoints expose user management and an audit log of authenticated API access.

**Core behaviors:**

- `GET /api/auth/me` returns the current signed-in user, if any.
- `POST /api/auth/login` validates username/password and creates the session.
- `POST /api/auth/logout` clears the session.
- `POST /api/auth/change-password` requires the current password before updating the hash.
- `GET /api/admin/users` lists all users.
- `POST /api/admin/users` creates users with `admin` or `user` role.
- `GET /api/admin/audit-logs` returns access log entries filtered by username, action, or target.
- Successful API access is written to `access_logs` by the shared audit hook.

**Bootstrap credentials:**

- `ADMIN_USERNAME` default: `admin`
- `ADMIN_PASSWORD` default: `admin12345`
- `ADMIN_FULL_NAME` default: `Administrator`

**Important note:**

- Change the default admin password before exposing the app outside a trusted local environment.

---

## 9. Data Directory

The `data/` directory is the default location for persistent data files:

```
data/
├── all_hpo_terms.csv         # ~19,500 HPO terms (CSV seed source)
│                              # Columns: hpo_id, term_name, definition, synonyms
├── vcf/                      # VCF file storage
│   └── <lab_number>/         # Per-patient subdirectory
│       └── *.vcf / *.vcf.gz / *.bcf
└── variant_uploads/          # Raw singleton/trio variant uploads
   └── <lab_number>/
      ├── singleton/
      │   └── *.xlsx / *.xls
      └── trio/
         └── *.xlsx / *.xls
└── local_ai/                 # Local LLM runtime and model weights
   ├── bin/
   └── models/
```

The entire `data/` directory can be relocated by setting the `DATA_DIR` environment variable. This enables:

- **NFS mounts** for shared lab storage.
- **SSHFS** for remote server access.
- **S3-Fuse** (s3fs, goofys) for cloud storage.

---

## 10. Environment Variables Reference

| Variable                    | Default                                      | Used In            | Description                                                 |
| --------------------------- | -------------------------------------------- | ------------------ | ----------------------------------------------------------- |
| `FLASK_ENV`                 | `development`                                | `run.py`           | Config selection (dev/production)                           |
| `SECRET_KEY`                | `dev-secret-key-...`                         | `config.py`        | Flask session secret key                                    |
| `MYSQL_USER`                | `root`                                       | `config.py`        | MySQL username                                              |
| `MYSQL_PASSWORD`            | (empty)                                      | `config.py`        | MySQL password                                              |
| `MYSQL_HOST`                | `localhost`                                  | `config.py`        | MySQL host                                                  |
| `MYSQL_PORT`                | `3306`                                       | `config.py`        | MySQL port                                                  |
| `MYSQL_DB`                  | `patient_db`                                 | `config.py`        | MySQL database name                                         |
| `DATA_DIR`                  | `<project_root>/data`                        | `config.py`        | Root directory for VCF, raw variant uploads, and data files |
| `LOCAL_AI_DIR`              | `DATA_DIR/local_ai`                          | `config.py`        | Root directory for local LLM binaries and model weights     |
| `LOCAL_AI_BIN_DIR`          | `LOCAL_AI_DIR/bin`                           | `config.py`        | Directory for llama.cpp binaries or wrappers                |
| `LOCAL_AI_MODELS_DIR`       | `LOCAL_AI_DIR/models`                        | `config.py`        | Directory for GGUF model files                              |
| `LOCAL_LLM_BASE_URL`        | `http://127.0.0.1:8080/v1/chat/completions`  | `config.py`        | Loopback OpenAI-compatible chat endpoint                    |
| `LOCAL_LLM_MODEL_FILE`      | `LOCAL_AI_MODELS_DIR/Qwen3.5-4B-Q4_K_M.gguf` | `config.py`        | Preferred GGUF model file                                   |
| `LOCAL_LLM_MODEL`           | `qwen3.5-4b-instruct`                        | `config.py`        | Default model name sent to the local server                 |
| `LOCAL_LLM_TIMEOUT`         | `120`                                        | `config.py`        | Upstream request timeout in seconds                         |
| `RAG_ENABLED`               | `1`                                          | `config.py`        | Enables local corpus retrieval for assistant prompts        |
| `RAG_CORPUS_PATH`           | `DATA_DIR/rag/corpus/corpus.jsonl`           | `config.py`        | On-disk chunked corpus used for retrieval                   |
| `RAG_MAX_CONTEXT_CHUNKS`    | `4`                                          | `config.py`        | Maximum retrieved chunks injected into each prompt          |
| `RAG_MAX_CONTEXT_CHARS`     | `6000`                                       | `config.py`        | Maximum total RAG context characters injected into prompts  |
| `RUN_LOCAL_LLM`             | `1`                                          | `run.sh`           | Starts the local LLM server alongside the app               |
| `VARIANT_UPLOAD_DIR`        | `DATA_DIR/variant_uploads`                   | `config.py`        | Raw singleton/trio upload storage path (derived)            |
| `MAX_UPLOAD_MB`             | `5000`                                       | `config.py`        | Maximum upload size in megabytes                            |
| `CORS_ORIGINS`              | (none)                                       | `app.py`           | Comma-separated allowed origins                             |
| `GUNICORN_BIND`             | `0.0.0.0:8000`                               | `gunicorn.conf.py` | Server bind address                                         |
| `GUNICORN_WORKERS`          | `(CPUs × 2) + 1`                             | `gunicorn.conf.py` | Number of worker processes                                  |
| `GUNICORN_WORKER_CLASS`     | `gthread`                                    | `gunicorn.conf.py` | Worker type                                                 |
| `GUNICORN_THREADS`          | `4`                                          | `gunicorn.conf.py` | Threads per worker                                          |
| `GUNICORN_TIMEOUT`          | `120`                                        | `gunicorn.conf.py` | Worker timeout (seconds)                                    |
| `GUNICORN_GRACEFUL_TIMEOUT` | `30`                                         | `gunicorn.conf.py` | Graceful shutdown timeout                                   |
| `GUNICORN_ACCESS_LOG`       | `-` (stdout)                                 | `gunicorn.conf.py` | Access log destination                                      |
| `GUNICORN_ERROR_LOG`        | `-` (stderr)                                 | `gunicorn.conf.py` | Error log destination                                       |
| `GUNICORN_LOG_LEVEL`        | `info`                                       | `gunicorn.conf.py` | Log verbosity                                               |

---

## 11. Production Deployment

### Architecture

In production, the app is served by **Gunicorn** (a pre-fork WSGI server) which spawns multiple worker processes, each capable of handling concurrent requests via threads. Flask serves both the REST API and the pre-built React SPA.

```
[Client] → [Reverse Proxy (nginx/Caddy)] → [Gunicorn :8000] → [Flask App]
                  HTTPS                        HTTP
```

### Files

| File                         | Purpose                                                       |
| ---------------------------- | ------------------------------------------------------------- |
| `gunicorn.conf.py`           | Gunicorn configuration (workers, threads, timeouts, hooks)    |
| `run.sh`                     | One-command script: setup, development, or production startup |
| `scripts/start_local_llm.py` | Local LLM launcher / mock server helper                       |
| `.env.example`               | Template for environment variables                            |
| `backend/config.py`          | `ProductionConfig` class (DEBUG=False, requires SECRET_KEY)   |

### Quick Start

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and MYSQL_PASSWORD

# 2. Generate a secret key
python -c "import secrets; print(secrets.token_hex(32))"

# 3. Start
chmod +x run.sh
bash run.sh production
```

`run.sh production` performs these steps:

1. Loads `.env` file if present.
2. Activates the Python virtual environment (`venv/` or `.venv/`).
3. Validates `SECRET_KEY` is set.
4. Builds the frontend (`npm install && npm run build`).
5. Installs Python dependencies.
6. Starts the local LLM server on `127.0.0.1:8080` unless `RUN_LOCAL_LLM=0` is set.
7. Starts Gunicorn with the production config.

### Gunicorn Configuration

All Gunicorn settings in `gunicorn.conf.py` are overridable via environment variables:

| Variable                    | Default               | Description                               |
| --------------------------- | --------------------- | ----------------------------------------- |
| `GUNICORN_BIND`             | `0.0.0.0:8000`        | Address and port to bind                  |
| `GUNICORN_WORKERS`          | `(CPU cores × 2) + 1` | Number of worker processes                |
| `GUNICORN_WORKER_CLASS`     | `gthread`             | Worker type (`sync`, `gthread`, `gevent`) |
| `GUNICORN_THREADS`          | `4`                   | Threads per worker                        |
| `GUNICORN_TIMEOUT`          | `120`                 | Worker timeout in seconds                 |
| `GUNICORN_GRACEFUL_TIMEOUT` | `30`                  | Graceful shutdown timeout                 |
| `GUNICORN_KEEPALIVE`        | `5`                   | Keep-alive timeout for connections        |
| `GUNICORN_ACCESS_LOG`       | `-` (stdout)          | Access log file path                      |
| `GUNICORN_ERROR_LOG`        | `-` (stderr)          | Error log file path                       |
| `GUNICORN_LOG_LEVEL`        | `info`                | Log level (debug, info, warning, error)   |

**Server hooks** are configured for lifecycle logging: `on_starting`, `post_fork`, `pre_exec`, `worker_exit`.

### Production Configuration Class

`ProductionConfig` (in `backend/config.py`):

- `DEBUG = False`
- `SECRET_KEY` — read from environment only (no default). `init_app()` raises `RuntimeError` if not set.
- CORS is restricted to origins listed in `CORS_ORIGINS` (comma-separated).

### Production Checklist

1. **Set `SECRET_KEY`** to a strong random value (required, enforced at startup).
2. **Set `MYSQL_PASSWORD`** and use a non-root MySQL user.
3. **Build the frontend**: `cd frontend && npm ci && npm run build`.
4. **Configure `CORS_ORIGINS`** if the frontend is served from a different domain.
5. **Configure `MAX_UPLOAD_MB`** appropriately for expected VCF file sizes.
6. **Set `DATA_DIR`** to a backed-up, high-availability storage location.
7. **Set up MySQL backups** for the `patient_db` database.
8. **Use HTTPS** via a reverse proxy (nginx, Caddy) in front of Gunicorn.
9. **Monitor workers** — adjust `GUNICORN_WORKERS` and `GUNICORN_THREADS` based on load.
10. **Log to files** in production — set `GUNICORN_ACCESS_LOG` and `GUNICORN_ERROR_LOG` to file paths.

### Reverse Proxy (nginx example)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;

    client_max_body_size 5000M;  # Match MAX_UPLOAD_MB

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;  # Match GUNICORN_TIMEOUT
    }
}
```

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
| `gunicorn`         | Production WSGI server                         |
| `pandas`           | Data manipulation (used in seed scripts)       |
| `pyhpo`            | Human Phenotype Ontology library (HPO refresh) |
| `openpyxl`         | Excel file reading/writing (.xlsx)             |
| `python-docx`      | Word document generation (.docx reports)       |
