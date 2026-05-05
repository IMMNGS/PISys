from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ── Association table (many-to-many: patients ↔ HPO terms) ──────────────
patient_hpo = db.Table(
    "patient_hpo",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("patient_id", db.Integer, db.ForeignKey("patients.id"), nullable=False),
    db.Column("hpo_term_id", db.Integer, db.ForeignKey("hpo_terms.id"), nullable=False),
    db.Column("date_added", db.DateTime, default=lambda: datetime.now(timezone.utc)),
    db.UniqueConstraint("patient_id", "hpo_term_id", name="uq_patient_hpo"),
)

patient_disease_term = db.Table(
    "patient_disease_term",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("patient_id", db.Integer, db.ForeignKey("patients.id"), nullable=False),
    db.Column("disease_term_id", db.Integer, db.ForeignKey("disease_terms.id"), nullable=False),
    db.Column("date_added", db.DateTime, default=lambda: datetime.now(timezone.utc)),
    db.UniqueConstraint("patient_id", "disease_term_id", name="uq_patient_disease_term"),
)


class HPOTerm(db.Model):
    """Human Phenotype Ontology term — reference data."""
    __tablename__ = "hpo_terms"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hpo_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    term_name = db.Column(db.String(500), nullable=False)
    definition = db.Column(db.Text, nullable=True)
    synonyms = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "hpo_id": self.hpo_id,
            "term_name": self.term_name,
            "definition": self.definition,
            "synonyms": self.synonyms,
        }


class DiseaseTerm(db.Model):
    """Free-text disease term used when no canonical HPO term is available."""
    __tablename__ = "disease_terms"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    term_name = db.Column(db.String(500), nullable=False)
    normalized_name = db.Column(db.String(500), unique=True, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "term_name": self.term_name,
            "normalized_name": self.normalized_name,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Patient(db.Model):
    """Patient record — stored in patients_db (default)."""
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_date = db.Column(db.Date, nullable=True)
    lab_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    im_lab_number = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(200), nullable=True)
    hkid = db.Column(db.String(50), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    sex = db.Column(db.String(20), nullable=True)
    age = db.Column(db.String(50), nullable=True)
    age_unit = db.Column(db.String(20), nullable=True)
    ethnicity = db.Column(db.String(100), nullable=True)
    specimen_collected = db.Column(db.Date, nullable=True)
    specimen_arrived = db.Column(db.Date, nullable=True)
    case_history = db.Column(db.Text, nullable=True)
    type_of_test = db.Column(db.String(200), nullable=True)
    type_of_findings = db.Column(db.String(200), nullable=True)
    findings_summary = db.Column(db.Text, nullable=True)
    ngs_batch = db.Column(db.String(100), nullable=True)
    ngs_tat = db.Column(db.String(100), nullable=True)
    ngs_tat_final = db.Column(db.String(100), nullable=True)
    request_dr = db.Column(db.String(200), nullable=True)
    remark = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # One-to-many: a patient can have many singleton findings
    singletons = db.relationship("Singleton", backref="patient", lazy="dynamic",
                                 cascade="all, delete-orphan")

    # One-to-many: a patient can have many trio findings
    trios = db.relationship("Trio", backref="patient", lazy="dynamic",
                            cascade="all, delete-orphan")

    # One-to-many: a patient can have many VCF files
    vcf_files = db.relationship("VcfFile", backref="patient", lazy="dynamic",
                                cascade="all, delete-orphan")

    # One-to-many: a patient can have many uploaded raw variant files
    variant_uploads = db.relationship(
        "VariantUpload", backref="patient", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # One-to-many: a patient can have many QC records
    ngs_qc = db.relationship(
        "NgsQc", backref="patient", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # Many-to-many: a patient can have many HPO terms
    hpo_terms = db.relationship("HPOTerm", secondary=patient_hpo, lazy="select",
                                backref=db.backref("patients", lazy="dynamic"))
    disease_terms = db.relationship("DiseaseTerm", secondary=patient_disease_term, lazy="select",
                                    backref=db.backref("patients", lazy="dynamic"))

    @property
    def clinical_history(self):
        return self.case_history

    @clinical_history.setter
    def clinical_history(self, value):
        self.case_history = value

    def to_dict(self, include_hpo=True, include_singletons=False,
                include_trios=False, include_vcf_files=False,
                include_variant_uploads=False,
                include_disease_terms=False):
        data = {
            "id": self.id,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "lab_number": self.lab_number,
            "im_lab_number": self.im_lab_number,
            "name": self.name,
            "hkid": self.hkid,
            "dob": self.dob.isoformat() if self.dob else None,
            "sex": self.sex,
            "age": self.age,
            "age_unit": self.age_unit,
            "ethnicity": self.ethnicity,
            "specimen_collected": self.specimen_collected.isoformat() if self.specimen_collected else None,
            "specimen_arrived": self.specimen_arrived.isoformat() if self.specimen_arrived else None,
            "clinical_history": self.clinical_history,
            "case_history": self.case_history,
            "type_of_test": self.type_of_test,
            "type_of_findings": self.type_of_findings,
            "findings_summary": self.findings_summary,
            "ngs_batch": self.ngs_batch,
            "ngs_tat": self.ngs_tat,
            "ngs_tat_final": self.ngs_tat_final,
            "request_dr": self.request_dr,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_hpo:
            data["hpo_terms"] = [t.to_dict() for t in self.hpo_terms]
        else:
            data["hpo_terms"] = []
        if include_disease_terms:
            data["disease_terms"] = [t.to_dict() for t in self.disease_terms]
        if include_singletons:
            data["singletons"] = [s.to_dict() for s in self.singletons]
        if include_trios:
            data["trios"] = [t.to_dict() for t in self.trios]
        else:
            data["trios"] = []
        if include_vcf_files:
            data["vcf_files"] = [v.to_dict() for v in self.vcf_files]
        else:
            data["vcf_files"] = []
        if include_variant_uploads:
            data["variant_uploads"] = [v.to_dict() for v in self.variant_uploads]
        else:
            data["variant_uploads"] = []
        return data


class Singleton(db.Model):
    """Singleton variant finding — stored in patients_db (default).
    Each row is linked to a patient via patient_id FK."""
    __tablename__ = "singleton"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    reportable_variant = db.Column(db.Text, nullable=True)
    chr_pos = db.Column(db.String(200), nullable=True)
    ref_alt = db.Column(db.String(500), nullable=True)
    igv_review = db.Column(db.Boolean, nullable=True, default=False)
    second_review_comment = db.Column(db.Text, nullable=True)
    gene_names = db.Column(db.Text, nullable=True)
    hgvs_c = db.Column(db.String(500), nullable=True)
    hgvs_p = db.Column(db.String(500), nullable=True)
    exon_number = db.Column(db.String(100), nullable=True)
    zygosity = db.Column(db.String(50), nullable=True)
    inheritance = db.Column(db.String(100), nullable=True)
    inherited_from = db.Column(db.String(100), nullable=True)
    classification = db.Column(db.String(200), nullable=True)
    omim_id = db.Column(db.String(50), nullable=True)
    rsid = db.Column(db.String(50), nullable=True)
    title = db.Column(db.String(500), nullable=True)
    omimid = db.Column(db.String(50), nullable=True)
    gene_region_combined = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "reportable_variant": self.reportable_variant,
            "chr_pos": self.chr_pos,
            "ref_alt": self.ref_alt,
            "igv_review": self.igv_review,
            "second_review_comment": self.second_review_comment,
            "gene_names": self.gene_names,
            "hgvs_c": self.hgvs_c,
            "hgvs_p": self.hgvs_p,
            "exon_number": self.exon_number,
            "zygosity": self.zygosity,
            "inheritance": self.inheritance,
            "inherited_from": self.inherited_from,
            "classification": self.classification,
            "omim_id": self.omim_id,
            "rsid": self.rsid,
            "title": self.title,
            "omimid": self.omimid,
            "gene_region_combined": self.gene_region_combined,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Trio(db.Model):
    """Trio variant finding.
    Each row is linked to a patient via patient_id FK."""
    __tablename__ = "trio"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    reportable_variant = db.Column(db.Text, nullable=True)
    chr_pos = db.Column(db.String(200), nullable=True)
    ref_alt = db.Column(db.String(500), nullable=True)
    igv_review = db.Column(db.Boolean, nullable=True, default=False)
    second_review_comment = db.Column(db.Text, nullable=True)
    gene_names = db.Column(db.Text, nullable=True)
    hgvs_c = db.Column(db.String(500), nullable=True)
    hgvs_p = db.Column(db.String(500), nullable=True)
    exon_number = db.Column(db.String(100), nullable=True)
    zygosity = db.Column(db.String(50), nullable=True)
    inheritance = db.Column(db.String(100), nullable=True)
    inherited_from = db.Column(db.String(100), nullable=True)
    classification = db.Column(db.String(200), nullable=True)
    omim_id = db.Column(db.String(50), nullable=True)
    rsid = db.Column(db.String(50), nullable=True)
    title = db.Column(db.String(500), nullable=True)
    omimid = db.Column(db.String(50), nullable=True)
    gene_region_combined = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "reportable_variant": self.reportable_variant,
            "chr_pos": self.chr_pos,
            "ref_alt": self.ref_alt,
            "igv_review": self.igv_review,
            "second_review_comment": self.second_review_comment,
            "gene_names": self.gene_names,
            "hgvs_c": self.hgvs_c,
            "hgvs_p": self.hgvs_p,
            "exon_number": self.exon_number,
            "zygosity": self.zygosity,
            "inheritance": self.inheritance,
            "inherited_from": self.inherited_from,
            "classification": self.classification,
            "omim_id": self.omim_id,
            "rsid": self.rsid,
            "title": self.title,
            "omimid": self.omimid,
            "gene_region_combined": self.gene_region_combined,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VcfFile(db.Model):
    """Tracks an uploaded VCF file. The binary lives on disk under VCF_DIR;
    this row stores its metadata and relative path."""
    __tablename__ = "vcf_files"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    filename = db.Column(db.String(500), nullable=False)
    relative_path = db.Column(db.String(1000), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "filename": self.filename,
            "relative_path": self.relative_path,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class VariantUpload(db.Model):
    """Tracks raw uploaded singleton/trio spreadsheet files.

    The binary file lives on disk under VARIANT_UPLOAD_DIR; this table stores
    metadata and relative path for audit/reprocessing.
    """
    __tablename__ = "variant_uploads"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    file_type = db.Column(db.String(20), nullable=False)  # singleton | trio
    original_filename = db.Column(db.String(500), nullable=False)
    stored_filename = db.Column(db.String(500), nullable=False)
    relative_path = db.Column(db.String(1000), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "file_type": self.file_type,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "relative_path": self.relative_path,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class NgsQc(db.Model):
    """QC metrics for an NGS run linked to a patient.

    Two QC file types are supported: ``panel`` (panel-of-genes test) and
    ``exome`` (whole-exome). The three report-critical metrics are
    extracted into dedicated columns; all raw rows from the QC file are
    preserved as JSON in ``metrics`` for downstream analysis/plotting.
    """
    __tablename__ = "ngs_qc"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    qc_type = db.Column(db.String(20), nullable=False, default="panel")  # panel | exome

    # Batch label parsed from the QC filename — e.g. "26P1" (yy=year, P=panel, x=batch number)
    batch = db.Column(db.String(40), nullable=True, index=True)

    # Report-critical metrics (rendered into the report's QC table)
    median_coverage = db.Column(db.Float, nullable=True)
    pct_20x = db.Column(db.Float, nullable=True)
    uniformity_pct = db.Column(db.Float, nullable=True)

    pass_fail = db.Column(db.String(20), nullable=True)  # PASS | FAIL | BORDERLINE
    notes = db.Column(db.Text, nullable=True)

    # Full raw metric set for THIS sample (JSON dict of every row in the QC file)
    metrics = db.Column(db.Text, nullable=True)

    # Positive control values from the same run (JSON dict, mirrors `metrics`)
    positive_control = db.Column(db.Text, nullable=True)

    original_filename = db.Column(db.String(500), nullable=True)
    relative_path = db.Column(db.String(1000), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        def _load(blob):
            try:
                return json.loads(blob) if blob else {}
            except (TypeError, ValueError):
                return {}
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "qc_type": self.qc_type,
            "batch": self.batch,
            "median_coverage": self.median_coverage,
            "pct_20x": self.pct_20x,
            "uniformity_pct": self.uniformity_pct,
            "pass_fail": self.pass_fail,
            "notes": self.notes,
            "metrics": _load(self.metrics),
            "positive_control": _load(self.positive_control),
            "original_filename": self.original_filename,
            "relative_path": self.relative_path,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class NgsQcBatch(db.Model):
    """One row per QC file upload, independent of patient matches.

    Even when a QC file contains no recognisable patient lab numbers,
    the upload is persisted here so the positive control and batch
    metadata are not lost.
    """
    __tablename__ = "ngs_qc_batches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    qc_type = db.Column(db.String(20), nullable=False, default="panel")  # panel | exome
    batch = db.Column(db.String(40), nullable=True, index=True)

    # Positive control metadata from the uploaded file
    positive_control_label = db.Column(db.String(500), nullable=True)
    positive_control = db.Column(db.Text, nullable=True)  # JSON dict

    original_filename = db.Column(db.String(500), nullable=True)
    relative_path = db.Column(db.String(1000), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Summary of what happened during upload
    matched_count = db.Column(db.Integer, nullable=False, default=0)
    unmatched_labels = db.Column(db.Text, nullable=True)  # JSON list

    def to_dict(self):
        import json
        def _load(blob):
            try:
                return json.loads(blob) if blob else {}
            except (TypeError, ValueError):
                return {}
        return {
            "id": self.id,
            "qc_type": self.qc_type,
            "batch": self.batch,
            "positive_control_label": self.positive_control_label,
            "positive_control": _load(self.positive_control),
            "original_filename": self.original_filename,
            "relative_path": self.relative_path,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "matched_count": self.matched_count,
            "unmatched_labels": _load(self.unmatched_labels),
        }


class VariantAuditLog(db.Model):
    """Records field-level changes to variant records for CAP/CLIA audit trails."""

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    variant_type = db.Column(db.String(20), nullable=False)  # singleton | trio
    variant_id = db.Column(db.Integer, nullable=False, index=True)
    field_name = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    changed_by = db.Column(db.String(80), nullable=False)
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "variant_type": self.variant_type,
            "variant_id": self.variant_id,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }


class AuthUser(db.Model):
    """Application user account used for login and role checks."""
    __tablename__ = "auth_users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(200), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user", index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

    @property
    def is_admin(self):
        return (self.role or "").lower() == "admin"


class AccessLog(db.Model):
    """Audit record of authenticated API access."""
    __tablename__ = "access_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("auth_users.id"), nullable=True, index=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    action = db.Column(db.String(40), nullable=False, index=True)
    target = db.Column(db.String(500), nullable=False, index=True)
    method = db.Column(db.String(10), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    remote_addr = db.Column(db.String(120), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("AuthUser", backref=db.backref("access_log_entries", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "target": self.target,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "remote_addr": self.remote_addr,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
