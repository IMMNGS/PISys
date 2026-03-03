# Patient Information System

A full-stack application for managing Patient Information and storing them in MySQL.

**Backend:** Python / Flask / SQLAlchemy  
**Frontend:** TypeScript / React / Vite  
**Database:** MySQL

## Project Structure

```
HA/
├── backend/
│   ├── __init__.py
│   ├── app.py               # Flask factory – serves API + built SPA
│   ├── config.py             # MySQL & app configuration (env-var driven)
│   ├── models.py             # SQLAlchemy models (patients, hpo_terms, disease_terms, singleton, trio, vcf_files, variant_uploads, patient_hpo, patient_disease_term)
│   └── routes/
│       ├── __init__.py       # Blueprint registration
│       ├── disease_terms.py  # Free-text disease term endpoints (search, create, assign)
│       ├── helpers.py        # Shared constants & utilities
│       ├── hpo_terms.py      # HPO term endpoints (search, refresh from pyhpo)
│       ├── patients.py       # Patient CRUD, XLSX import, HPO assignment, paginated list & options
│       ├── singletons.py     # Singleton variant CRUD + XLSX import
│       ├── trios.py          # Trio variant CRUD + XLSX import
│       ├── vcf.py            # VCF file upload, list, delete
│       └── reports.py        # Report preview & .docx generation
│
├── data/                     # Data directory (local now, remote-mountable in future)
│   ├── all_hpo_terms.csv     # ~19,500 HPO terms (loadable via Manage HPO page)
│   └── vcf/                  # VCF files uploaded per patient
│   └── variant_uploads/       # Original singleton/trio XLSX files (per patient, per file type)
│
├── frontend/                 # React + TypeScript (Vite)
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts        # Dev proxy /api → Flask :5000
│   └── src/
│       ├── main.tsx
│       ├── App.tsx            # Routes (react-router-dom)
│       ├── index.css          # Global styles
│       ├── api/
│       │   └── client.ts     # Typed API client (with server-side pagination helpers)
│       ├── types/
│       │   └── index.ts      # TypeScript interfaces
│       ├── components/
│       │   ├── DropdownSelect.tsx   # Multi-select dropdown (used for HPO assignment)
│       │   ├── Navbar.tsx
│       │   └── SearchableSelect.tsx # Combobox single-select with server-side pagination
│       └── pages/
│           ├── Home.tsx
│           ├── PatientDetail.tsx
│           ├── SelectPatients.tsx   # Patient table with server-side filters & pagination
│           ├── Upload.tsx           # File upload with searchable patient selector
│           ├── Report.tsx           # Report generation with searchable lab number selector
│           └── ManageHpo.tsx
│
├── requirements.txt          # Python dependencies
├── run.py                    # Entry-point (dev: python run.py, prod: gunicorn run:app)
├── gunicorn.conf.py          # Gunicorn production server configuration
├── setup.sh                  # One-command setup script
├── start_production.sh       # One-command production start script
├── .env.example              # Environment variable template
└── README.md
```

## Quick Start

```bash
chmod +x run.sh
bash run.sh setup
```

The setup script will:

1. Check prerequisites (Python 3, Node.js, MySQL)
2. Install Python dependencies
3. Create the MySQL database
4. Create data directories (`data/`, `data/vcf/`, `data/variant_uploads/`)
5. Install frontend dependencies and build the React/TypeScript app

After setup, load HPO terms from the **Manage HPO** page (or `POST /api/hpo_terms/refresh`), then upload patient data via the **Upload** page.

Then open [http://localhost:5000](http://localhost:5000).

## Prerequisites

- Python 3.9+
- Node.js 18+
- MySQL 8.0+ (running locally or remotely)

## Manual Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Create the MySQL database

```sql
CREATE DATABASE IF NOT EXISTS patient_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Configure connection (optional)

Set environment variables or edit `backend/config.py`:

```bash
export MYSQL_USER=root
export MYSQL_PASSWORD=password
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DB=patient_db
```

### 4. Build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. Load HPO terms

Open the app and navigate to **Manage HPO** → click **Refresh from PyHPO**, or call the API:

```bash
curl -X POST http://localhost:5000/api/hpo_terms/refresh
```

### 6. Upload patient data

Use the **Upload** page to import patients, singletons, trios, and VCF files.
Sample files are provided in `data/sample/` for testing.

### 7. Run the app (development)

```bash
python run.py
```

Open [http://localhost:5001](http://localhost:5001).

## Development Mode

Run the Flask API and Vite dev server separately for hot-reload:

```bash
# Terminal 1 — API server
python run.py

# Terminal 2 — Vite dev server with HMR
cd frontend
npm run dev
```

Vite runs on port 3000 and proxies `/api/*` requests to Flask on port 5001.

## Production Deployment

The production setup uses **Gunicorn** as the WSGI server with multi-worker/threaded configuration.

### Quick Start (Production)

```bash
# 1. Copy and configure environment variables
cp .env.example .env

# 2. Generate a secret key
python -c "import secrets; print(secrets.token_hex(32))"
# Paste the output into .env as SECRET_KEY=<value>

# 3. Set your MySQL password and other vars in .env

# 4. Start production server
chmod +x run.sh
bash run.sh production
```

The server binds to `0.0.0.0:8000` by default, serving the built React SPA and API via Gunicorn.

### Manual Production Start

```bash
# Build frontend
cd frontend && npm ci && npm run build && cd ..

# Set environment
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Start Gunicorn
gunicorn -c gunicorn.conf.py run:app
```

### Production Configuration

All Gunicorn settings are configurable via environment variables or `.env`:

| Variable                    | Default               | Description                         |
| --------------------------- | --------------------- | ----------------------------------- |
| `GUNICORN_BIND`             | `0.0.0.0:8000`        | Address and port to bind            |
| `GUNICORN_WORKERS`          | `(CPU cores × 2) + 1` | Number of worker processes          |
| `GUNICORN_WORKER_CLASS`     | `gthread`             | Worker type (sync, gthread, gevent) |
| `GUNICORN_THREADS`          | `4`                   | Threads per worker                  |
| `GUNICORN_TIMEOUT`          | `120`                 | Worker timeout in seconds           |
| `GUNICORN_GRACEFUL_TIMEOUT` | `30`                  | Graceful shutdown timeout           |
| `GUNICORN_LOG_LEVEL`        | `info`                | Log level (debug, info, warning)    |
| `CORS_ORIGINS`              | (none)                | Comma-separated allowed origins     |

### Production Checklist

1. Set `SECRET_KEY` to a strong random value (required)
2. Set `MYSQL_PASSWORD` and use a non-root MySQL user
3. Set `CORS_ORIGINS` if the frontend is served from a different domain
4. Configure `MAX_UPLOAD_MB` for expected VCF file sizes
5. Set `DATA_DIR` to a backed-up, high-availability storage path
6. Put a reverse proxy (nginx, Caddy) in front for HTTPS
7. Set up MySQL backups for the `patient_db` database

## Pages

| Route           | Description                                                                                     |
| --------------- | ----------------------------------------------------------------------------------------------- |
| `/`             | Home dashboard – view all patients with search, HPO terms, and findings                         |
| `/patients/:id` | Detailed view of a single patient (singletons, trios, VCF files, HPO terms)                     |
| `/select`       | Select patients from a list for further analysis                                                |
| `/upload`       | Upload patient data, singleton/trio variants, and VCF files via XLSX                            |
| `/report`       | Generate and preview clinical .docx reports for a patient                                       |
| `/manage-hpo`   | Side-by-side searchable selectors to assign HPO terms; refresh button to pull latest from pyhpo |

## API Endpoints

### HPO Terms

| Method | Endpoint                                 | Description                                          |
| ------ | ---------------------------------------- | ---------------------------------------------------- |
| GET    | `/api/hpo_terms?search=&page=&per_page=` | Search/paginate HPO terms (by ID, name, or synonyms) |
| GET    | `/api/hpo_terms/<id>`                    | Get a single HPO term                                |
| POST   | `/api/hpo_terms/refresh`                 | Pull latest HPO terms from pyhpo and upsert into DB  |

### Patients

| Method | Endpoint                                                       | Description                                                     |
| ------ | -------------------------------------------------------------- | --------------------------------------------------------------- |
| GET    | `/api/patients?search=`                                        | List all patients (full nested data)                            |
| GET    | `/api/patients/options?search=&limit=&offset=`                 | Lightweight paginated list (id, lab_number, name) for dropdowns |
| GET    | `/api/patients/list?limit=&offset=&lab_number=&name=&sex=&...` | Paginated table view with per-column server-side filters        |
| GET    | `/api/patients/<id>`                                           | Get single patient (includes HPO, singletons, trios, VCFs)      |
| POST   | `/api/patients`                                                | Create a patient                                                |
| PUT    | `/api/patients/<id>`                                           | Update a patient                                                |
| DELETE | `/api/patients/<id>`                                           | Delete a patient                                                |
| POST   | `/api/patients/upload`                                         | Bulk import patients from XLSX                                  |
| POST   | `/api/patients/selected`                                       | Get full data for selected patient IDs                          |

### Patient ↔ HPO Assignment

| Method | Endpoint                             | Description                          |
| ------ | ------------------------------------ | ------------------------------------ |
| GET    | `/api/patients/<id>/hpo_terms`       | List HPO terms assigned to a patient |
| POST   | `/api/patients/assign_hpo`           | Assign HPO terms to patients         |
| DELETE | `/api/patients/<id>/hpo_terms/<tid>` | Remove an HPO term from a patient    |

### Free-Text Disease Terms

| Method | Endpoint                                      | Description                                                  |
| ------ | --------------------------------------------- | ------------------------------------------------------------ |
| GET    | `/api/disease_terms?search=&page=&per_page=`  | Search/paginate free-text disease terms                      |
| GET    | `/api/disease_terms/options?search=&limit=&offset=` | Lightweight dropdown options for disease terms         |
| POST   | `/api/disease_terms`                          | Create (or return existing) free-text disease term by name   |
| GET    | `/api/patients/<id>/disease_terms`            | List disease terms assigned to a patient                     |
| POST   | `/api/patients/assign_disease_terms`          | Assign disease terms to patients                             |
| DELETE | `/api/patients/<id>/disease_terms/<tid>`      | Remove a disease term from a patient                         |

### Singleton Variants

| Method | Endpoint                              | Description                           |
| ------ | ------------------------------------- | ------------------------------------- |
| GET    | `/api/patients/<id>/singletons`       | List singleton findings for a patient |
| POST   | `/api/patients/<id>/singletons`       | Create a singleton finding            |
| GET    | `/api/singletons/<id>`                | Get a single singleton finding        |
| PUT    | `/api/singletons/<id>`                | Update a singleton finding            |
| DELETE | `/api/singletons/<id>`                | Delete a singleton finding            |
| POST   | `/api/patients/<id>/upload/singleton` | Import singleton variants from XLSX and retain the original file on disk |

### Trio Variants

| Method | Endpoint                         | Description                      |
| ------ | -------------------------------- | -------------------------------- |
| GET    | `/api/patients/<id>/trios`       | List trio findings for a patient |
| POST   | `/api/patients/<id>/trios`       | Create a trio finding            |
| PUT    | `/api/trios/<id>`                | Update a trio finding            |
| DELETE | `/api/trios/<id>`                | Delete a trio finding            |
| POST   | `/api/patients/<id>/upload/trio` | Import trio variants from XLSX and retain the original file on disk |

### VCF Files

| Method | Endpoint                 | Description                     |
| ------ | ------------------------ | ------------------------------- |
| GET    | `/api/patients/<id>/vcf` | List VCF files for a patient    |
| POST   | `/api/patients/<id>/vcf` | Upload a VCF file for a patient |
| DELETE | `/api/vcf_files/<id>`    | Delete a VCF file (disk + DB)   |

### Report Generation

| Method | Endpoint               | Description                                   |
| ------ | ---------------------- | --------------------------------------------- |
| POST   | `/api/report/preview`  | Preview report data before generating .docx   |
| POST   | `/api/report/generate` | Generate and download a clinical .docx report |

## Database Schema

- **hpo_terms** — `id`, `hpo_id` (unique), `term_name`, `definition`, `synonyms`
- **disease_terms** — `id`, `term_name`, `normalized_name` (unique + indexed), `notes`, `created_at`
- **patients** — `id`, `report_date`, `lab_number` (unique), `im_lab_number`, `name`, `hkid`, `dob`, `sex`, `age`, `age_unit`, `ethnicity`, `specimen_collected`, `specimen_arrived`, `clinical_history` (stored in DB column `case_history`), `type_of_test`, `type_of_findings`, `findings_summary`, `ngs_batch`, `ngs_tat`, `ngs_tat_final`, `request_dr`, `remark`, `created_at`
- **singleton** — `id`, `patient_id` (FK → patients), `reportable_variant`, `chr_pos`, `ref_alt`, `igv_review`, `second_review_comment`, `gene_names`, `hgvs_c`, `hgvs_p`, `exon_number`, `zygosity`, `inheritance`, `inherited_from`, `classification`, `omim_id`, `rsid`, `title`, `omimid`, `gene_region_combined`, `created_at`
- **trio** — same columns as singleton
- **vcf_files** — `id`, `patient_id` (FK → patients), `filename`, `relative_path`, `file_size`, `uploaded_at`
- **variant_uploads** — `id`, `patient_id` (FK → patients), `file_type` (`singleton`/`trio`), `original_filename`, `stored_filename`, `relative_path`, `file_size`, `uploaded_at`
- **patient_hpo** — many-to-many join: `id`, `patient_id` (FK → patients), `hpo_term_id` (FK → hpo_terms), `date_added`
- **patient_disease_term** — many-to-many join: `id`, `patient_id` (FK → patients), `disease_term_id` (FK → disease_terms), `date_added`

## Data Directory

The `data/` directory stores reference data and uploaded files:

- `data/all_hpo_terms.csv` — ~19,500 HPO terms (loadable via Manage HPO page or `POST /api/hpo_terms/refresh`)
- `data/vcf/` — VCF files uploaded per patient (`.vcf`, `.vcf.gz`, `.bcf`)
- `data/variant_uploads/` — original uploaded singleton/trio variant spreadsheets (`.xlsx`, `.xls`) grouped by patient and file type
- `data/sample/` — Sample XLSX and VCF files for testing the full upload workflow

The data path is configurable via the `DATA_DIR` environment variable, making it easy to point to a remote/mounted filesystem in production.

## Server-Side Pagination

Patient-related views use **server-side pagination** to handle large datasets efficiently:

- **Dropdowns** (Report lab number selector, Upload patient selector): Use the `SearchableSelect` component backed by `/api/patients/options`, loading 20 items initially with a "Load more" button fetching 100 more per click.
- **Patient table** (`/select`): Uses `/api/patients/list` with per-column server-side filters and paginated loading — 20 patients initially, 100 more per "Load more" click.
- **HPO terms**: The `/api/hpo_terms` endpoint supports `page` and `per_page` pagination.
