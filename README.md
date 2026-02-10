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
│   ├── generate_mock_data.py # Generate 1,000 realistic mock patients for load testing
│   ├── models.py             # SQLAlchemy models (patients, hpo_terms, singleton, trio, vcf_files, patient_hpo)
│   ├── seed.py               # Seed script – loads HPO CSV + mock patients
│   └── routes/
│       ├── __init__.py       # Blueprint registration
│       ├── helpers.py        # Shared constants & utilities
│       ├── hpo_terms.py      # HPO term endpoints (search, refresh from pyhpo)
│       ├── patients.py       # Patient CRUD, XLSX import, HPO assignment, paginated list & options
│       ├── singletons.py     # Singleton variant CRUD + XLSX import
│       ├── trios.py          # Trio variant CRUD + XLSX import
│       ├── vcf.py            # VCF file upload, list, delete
│       └── reports.py        # Report preview & .docx generation
│
├── data/                     # Data directory (local now, remote-mountable in future)
│   ├── all_hpo_terms.csv     # ~19,500 HPO terms (used by seed.py)
│   └── vcf/                  # VCF files uploaded per patient
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
├── run.py                    # Entry-point: python run.py
├── setup.sh                  # One-command setup script
└── README.md
```

## Quick Start

```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:

1. Check prerequisites (Python 3, Node.js, MySQL)
2. Install Python dependencies
3. Create the MySQL database
4. Create data directories (`data/`, `data/vcf/`)
5. Install frontend dependencies and build the React/TypeScript app
6. Seed the database with HPO terms + 20 mock patients

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

### 5. Seed the database

```bash
python -m backend.seed
```

### 6. Run the app

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000).

## Development Mode

Run the Flask API and Vite dev server separately for hot-reload:

```bash
# Terminal 1 — API server
python run.py

# Terminal 2 — Vite dev server with HMR
cd frontend
npm run dev
```

Vite runs on port 3000 and proxies `/api/*` requests to Flask on port 5000.

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

### Singleton Variants

| Method | Endpoint                              | Description                           |
| ------ | ------------------------------------- | ------------------------------------- |
| GET    | `/api/patients/<id>/singletons`       | List singleton findings for a patient |
| POST   | `/api/patients/<id>/singletons`       | Create a singleton finding            |
| GET    | `/api/singletons/<id>`                | Get a single singleton finding        |
| PUT    | `/api/singletons/<id>`                | Update a singleton finding            |
| DELETE | `/api/singletons/<id>`                | Delete a singleton finding            |
| POST   | `/api/patients/<id>/upload/singleton` | Import singleton variants from XLSX   |

### Trio Variants

| Method | Endpoint                         | Description                      |
| ------ | -------------------------------- | -------------------------------- |
| GET    | `/api/patients/<id>/trios`       | List trio findings for a patient |
| POST   | `/api/patients/<id>/trios`       | Create a trio finding            |
| PUT    | `/api/trios/<id>`                | Update a trio finding            |
| DELETE | `/api/trios/<id>`                | Delete a trio finding            |
| POST   | `/api/patients/<id>/upload/trio` | Import trio variants from XLSX   |

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
- **patients** — `id`, `report_date`, `lab_number` (unique), `im_lab_number`, `name`, `hkid`, `dob`, `sex`, `age`, `age_unit`, `ethnicity`, `specimen_collected`, `specimen_arrived`, `case_history`, `type_of_test`, `type_of_findings`, `findings_summary`, `ngs_batch`, `ngs_tat`, `ngs_tat_final`, `request_dr`, `remark`, `created_at`
- **singleton** — `id`, `patient_id` (FK → patients), `reportable_variant`, `chr_pos`, `ref_alt`, `igv_review`, `second_review_comment`, `gene_names`, `hgvs_c`, `hgvs_p`, `exon_number`, `zygosity`, `inheritance`, `inherited_from`, `classification`, `omim_id`, `rsid`, `title`, `omimid`, `gene_region_combined`, `created_at`
- **trio** — same columns as singleton
- **vcf_files** — `id`, `patient_id` (FK → patients), `filename`, `relative_path`, `file_size`, `uploaded_at`
- **patient_hpo** — many-to-many join: `id`, `patient_id` (FK → patients), `hpo_term_id` (FK → hpo_terms), `date_added`

## Data Directory

The `data/` directory stores generated assets and uploaded files:

- `data/all_hpo_terms.csv` — HPO terms CSV used by `seed.py` to populate the database
- `data/vcf/` — VCF files uploaded per patient (`.vcf`, `.vcf.gz`, `.bcf`)

The data path is configurable via the `DATA_DIR` environment variable, making it easy to point to a remote/mounted filesystem in production.

## Mock Data Generation

For load testing with a larger dataset, run the mock data generator:

```bash
source .venv/bin/activate
python -m backend.generate_mock_data
```

This creates **1,000 patients** with realistic randomized data including:

- Names, ethnicities, case histories, and doctor references
- Singleton and trio variants with real gene names, HGVS notation, and chromosomal positions
- HPO term assignments per patient

## Server-Side Pagination

Patient-related views use **server-side pagination** to handle large datasets efficiently:

- **Dropdowns** (Report lab number selector, Upload patient selector): Use the `SearchableSelect` component backed by `/api/patients/options`, loading 20 items initially with a "Load more" button fetching 100 more per click.
- **Patient table** (`/select`): Uses `/api/patients/list` with per-column server-side filters and paginated loading — 20 patients initially, 100 more per "Load more" click.
- **HPO terms**: The `/api/hpo_terms` endpoint supports `page` and `per_page` pagination.
