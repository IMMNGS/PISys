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
