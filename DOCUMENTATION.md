# Technical Documentation

## 1) System overview

The application is a patient information system for clinical genetics workflows. It combines:

- a Flask backend
- a React + TypeScript frontend
- a MySQL database
- on-disk storage for uploaded VCF and variant files
- optional Docker / Synology NAS deployment

The app supports:

- patient record management
- HPO term assignment
- free-text disease terms
- singleton and trio variant records
- VCF file uploads
- report generation
- descriptive statistics and insights
- login, CSRF protection, and audit logging

## 2) Repository map

### Top-level files

| File                    | Purpose                                                         |
| ----------------------- | --------------------------------------------------------------- |
| `README.md`             | Quick start, overview, and primary entry point for developers   |
| `DOCUMENTATION.md`      | Technical reference for structure, schema, and runtime behavior |
| `SYNOLOGY_SETUP.md`     | Step-by-step Synology NAS deployment guide                      |
| `TODO.md`               | Small list of follow-up items and future work                   |
| `.env.example`          | Local development environment template                          |
| `.env.synology.example` | Synology / Docker production environment template               |
| `docker-compose.yml`    | MySQL + app stack for Docker deployment                         |
| `Dockerfile`            | Production image build for the Flask app and frontend           |
| `gunicorn.conf.py`      | Gunicorn production server configuration                        |
| `requirements.txt`      | Python dependencies                                             |
| `run.py`                | Python application entry point                                  |
| `run.sh`                | Unix/macOS setup and launcher                                   |
| `run_windows.ps1`       | Windows PowerShell setup and launcher                           |
| `run_windows.bat`       | Windows batch wrapper for the PowerShell launcher               |

### Backend

| Path                  | Purpose                                                                           |
| --------------------- | --------------------------------------------------------------------------------- |
| `backend/app.py`      | Flask application factory, MySQL bootstrap, CORS, SPA fallback, table creation    |
| `backend/config.py`   | Environment-driven configuration and data directory paths                         |
| `backend/models.py`   | SQLAlchemy models and table definitions                                           |
| `backend/security.py` | Session auth, CSRF validation, password hashing, audit logging                    |
| `backend/routes/`     | API blueprints for authentication, patients, variants, HPO, reports, and insights |

### Frontend

| Path                       | Purpose                              |
| -------------------------- | ------------------------------------ |
| `frontend/src/main.tsx`    | React root bootstrap                 |
| `frontend/src/App.tsx`     | Router, auth gates, and layout shell |
| `frontend/src/index.css`   | Global styles and layout theme       |
| `frontend/src/components/` | Shared UI controls                   |
| `frontend/src/pages/`      | Page-level screens                   |
| `frontend/src/auth/`       | Client-side auth state helpers       |
| `frontend/src/api/`        | Frontend API client                  |
| `frontend/src/types/`      | Shared TypeScript types              |

### Data and scripts

| Path                     | Purpose                                                 |
| ------------------------ | ------------------------------------------------------- |
| `data/all_hpo_terms.csv` | HPO reference dataset used by seeding and lookup flows  |
| `data/disease_terms.csv` | Free-text disease term seed/reference file              |
| `data/vcf/`              | Persisted uploaded VCF files                            |
| `data/variant_uploads/`  | Persisted raw singleton/trio spreadsheet uploads        |
| `data/rag/`              | Local retrieval-augmented generation assets and corpora |
| `data/local_ai/`         | Local AI / model files and supporting binaries          |
| `scripts/seed_hpo.py`    | Seeds the HPO table from the pyHPO ontology             |
| `test/`                  | Backend integration and API tests                       |

### Legacy / ignored files

The repository still contains legacy scripts such as `backend/routes/patient_info`, `backend/routes/patient_info2`, and `backend/routes/patient_info3`. They are excluded by `.gitignore` and are not part of the current Flask runtime. They are kept only as historical references.

## 3) Runtime architecture

### Startup sequence

1. `run.py` loads `.env` and selects the runtime environment.
2. `backend.app.create_app()` creates the Flask application.
3. The app initializes SQLAlchemy, CORS, session security, and blueprints.
4. The MySQL database is created if needed.
5. SQLAlchemy `create_all()` ensures tables exist.
6. The default admin user is seeded if no users exist yet.
7. The frontend build is served from `frontend/dist` in production.

### Authentication flow

- Login is session-based.
- CSRF tokens are stored in the session and validated on non-GET API requests.
- Authentication is effectively enabled once at least one `auth_users` row exists.
- Admin-only routes require an `AuthUser` with `role = admin`.

### Audit logging

Successful authenticated API responses are logged to `access_logs`.
The log records user, action, request path, method, status code, remote IP, and user agent.

## 4) Backend modules

### `backend/app.py`

Responsibilities:

- create the Flask app
- configure CORS for development and production
- enforce auth and CSRF for API requests
- register blueprints
- serve the React SPA
- create the MySQL database if it does not exist
- create database tables and seed the default admin user

### `backend/config.py`

Responsibilities:

- read environment variables
- define MySQL connection settings
- define data directory paths
- enforce maximum upload size
- provide development and production config classes

### `backend/models.py`

Responsibilities:

- define all SQLAlchemy tables and relationships
- convert records to JSON-compatible dictionaries
- store HPO and disease-term metadata
- store patients, variants, VCF uploads, auth users, and access logs

### `backend/security.py`

Responsibilities:

- hash and verify passwords
- load the current session user
- create and validate CSRF tokens
- seed the default admin account
- enforce login/admin requirements
- log API access events

## 5) API route groups

All blueprints are registered under the `/api` prefix.

| Module                            | Main purpose                                        |
| --------------------------------- | --------------------------------------------------- |
| `backend/routes/auth.py`          | Login, logout, current-user, password change        |
| `backend/routes/admin.py`         | User administration and audit log access            |
| `backend/routes/patients.py`      | Patient CRUD, import, selections, filters, findings |
| `backend/routes/singletons.py`    | Singleton variant CRUD and patient-linked retrieval |
| `backend/routes/trios.py`         | Trio variant CRUD and patient-linked retrieval      |
| `backend/routes/vcf.py`           | VCF upload, listing, and deletion                   |
| `backend/routes/hpo_terms.py`     | HPO term search, options, refresh, and lookup       |
| `backend/routes/disease_terms.py` | Disease-term search, CRUD, and patient assignment   |
| `backend/routes/reports.py`       | Report preview and report generation                |
| `backend/routes/insights.py`      | Summary statistics and explanation endpoints        |

### Notable route families

- `/api/auth/*` — authentication
- `/api/admin/*` — administration
- `/api/patients/*` — patient records and bulk actions
- `/api/hpo_terms/*` — ontology lookup and refresh
- `/api/disease_terms/*` — free-text disease terms
- `/api/report/*` and `/api/reports/*` — report generation flows
- `/api/insights/*` — statistics and summary analysis

## 6) Database structure

The app uses MySQL via SQLAlchemy.

### `patients`

Primary patient record table.

Important columns:

- `id`
- `report_date`
- `lab_number` unique
- `im_lab_number`
- `name`
- `hkid`
- `dob`
- `sex`
- `age`
- `age_unit`
- `ethnicity`
- `specimen_collected`
- `specimen_arrived`
- `case_history` / `clinical_history`
- `type_of_test`
- `type_of_findings`
- `findings_summary`
- `ngs_batch`
- `ngs_tat`
- `ngs_tat_final`
- `request_dr`
- `remark`
- `created_at`

Relationships:

- one patient → many singleton findings
- one patient → many trio findings
- one patient → many VCF files
- one patient → many raw variant uploads
- many-to-many with HPO terms
- many-to-many with disease terms

### `hpo_terms`

Reference table for HPO ontology terms.

Important columns:

- `id`
- `hpo_id` unique
- `term_name`
- `definition`
- `synonyms`

### `disease_terms`

Free-text disease terms used when a canonical ontology term is not available.

Important columns:

- `id`
- `term_name`
- `normalized_name` unique
- `notes`
- `created_at`

### `singleton`

Singleton variant findings linked to a patient.

Important columns:

- `id`
- `patient_id`
- `reportable_variant`
- `chr_pos`
- `ref_alt`
- `igv_review`
- `second_review_comment`
- `gene_names`
- `hgvs_c`
- `hgvs_p`
- `exon_number`
- `zygosity`
- `inheritance`
- `inherited_from`
- `classification`
- `omim_id`
- `rsid`
- `title`
- `omimid`
- `gene_region_combined`
- `created_at`

### `trio`

Trio variant findings linked to a patient.

The `trio` table uses the same core field set as `singleton`, with `patient_id` as the foreign key.

### `vcf_files`

Metadata for uploaded VCF files.

Important columns:

- `id`
- `patient_id`
- `filename`
- `relative_path`
- `file_size`
- `uploaded_at`

### `variant_uploads`

Metadata for raw spreadsheet uploads used during patient/variant imports.

Important columns:

- `id`
- `patient_id`
- `file_type` (`singleton` or `trio`)
- `original_filename`
- `stored_filename`
- `relative_path`
- `file_size`
- `uploaded_at`

### `auth_users`

Application login accounts.

Important columns:

- `id`
- `username` unique
- `full_name`
- `password_hash`
- `role`
- `is_active`
- `created_at`
- `last_login_at`

### `access_logs`

Audit trail for authenticated API activity.

Important columns:

- `id`
- `user_id`
- `username`
- `action`
- `target`
- `method`
- `path`
- `status_code`
- `remote_addr`
- `user_agent`
- `created_at`

### Join tables

#### `patient_hpo`

Many-to-many link between patients and HPO terms.

Columns:

- `id`
- `patient_id`
- `hpo_term_id`
- `date_added`

Unique constraint:

- `(patient_id, hpo_term_id)`

#### `patient_disease_term`

Many-to-many link between patients and disease terms.

Columns:

- `id`
- `patient_id`
- `disease_term_id`
- `date_added`

Unique constraint:

- `(patient_id, disease_term_id)`

## 7) Frontend structure

### App shell

- `frontend/src/App.tsx` defines routes, authentication gating, and the shared layout shell.
- `frontend/src/main.tsx` mounts the React application.
- `frontend/src/index.css` holds the global theme and layout styles.

### Pages

| Page                   | Purpose                                     |
| ---------------------- | ------------------------------------------- |
| `Home.tsx`             | Main landing page after login               |
| `PatientDetail.tsx`    | Patient record and related findings         |
| `SelectPatients.tsx`   | Patient selection and table-based workflows |
| `ManageHpo.tsx`        | HPO term management and assignment          |
| `Upload.tsx`           | Upload patient or variant files             |
| `Report.tsx`           | Report preview and generation               |
| `DescriptiveStats.tsx` | Summary statistics and charts               |
| `Login.tsx`            | Authentication screen                       |
| `AdminAudit.tsx`       | Admin user and audit-log interface          |

### Shared components

| Component                   | Purpose                         |
| --------------------------- | ------------------------------- |
| `Navbar.tsx`                | Top navigation bar              |
| `DropdownSelect.tsx`        | Shared select control           |
| `SearchableSelect.tsx`      | Searchable single-select UI     |
| `SearchableMultiSelect.tsx` | Searchable multi-select UI      |
| `DistributionChart.tsx`     | Chart rendering for stats pages |

### Auth helpers

- `frontend/src/auth/authContext.ts` — authentication context provider
- `frontend/src/auth/useAuth.ts` — auth hook used by the router and UI

### API client and types

- `frontend/src/api/client.ts` — frontend HTTP client and request helpers
- `frontend/src/types/index.ts` — shared frontend types

### Frontend routes

- `/login`
- `/`
- `/patients/:id`
- `/select`
- `/upload`
- `/report`
- `/manage-hpo`
- `/stats`
- `/admin`

## 8) Data directories

### `data/`

Default local data root. Paths can be overridden with `DATA_DIR`.

### `data/vcf/`

Stores uploaded VCF files for each patient.

### `data/variant_uploads/`

Stores raw spreadsheet uploads for audit and reprocessing.

### `data/rag/`

Contains retrieval-augmented generation source material and corpus organization.

### `data/local_ai/`

Local model and runtime assets for offline AI-related experiments.

## 9) Environment variables

### Database

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DB`

### Security and auth

- `SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_FULL_NAME`

### Runtime and uploads

- `FLASK_ENV`
- `PORT`
- `DATA_DIR`
- `MAX_UPLOAD_MB`
- `CORS_ORIGINS`

### Gunicorn

- `GUNICORN_BIND`
- `GUNICORN_WORKERS`
- `GUNICORN_THREADS`
- `GUNICORN_TIMEOUT`
- `GUNICORN_GRACEFUL_TIMEOUT`
- `GUNICORN_KEEPALIVE`
- `GUNICORN_LOG_LEVEL`

## 10) Development workflow

### Setup

1. Create `.env` from `.env.example`.
2. Run `bash run.sh setup` on Unix/macOS or `run_windows.ps1 setup` on Windows.
3. Start the app in development or production mode.

### Tests

- Backend tests: `test/`
- Frontend tests: `frontend/src/__tests__/`

### Build and serve

- Development frontend: `cd frontend && npm run dev`
- Production frontend build: `cd frontend && npm run build`
- Production backend: `gunicorn -c gunicorn.conf.py run:app`

## 11) Deployment notes

### Docker

The Docker stack uses:

- `mysql:8.0` for the database
- a Python runtime image for the Flask app
- bind-mounted volumes for persistent MySQL data and application uploads

### Synology NAS

The Synology guide in `SYNOLOGY_SETUP.md` uses:

- `/volume1/docker/ha/mysql` for MySQL persistence
- `/volume1/docker/ha/app/data` for uploaded files
- `/volume1/docker/ha/.env` for production secrets and configuration

### Production behavior

- Flask serves the compiled React app from `frontend/dist`
- Gunicorn binds to port `8000` inside the container or local process
- Docker maps the app to host port `18000` by default
