"""VCF file management routes."""

import os

from flask import Blueprint, abort, jsonify, request, current_app
from werkzeug.utils import secure_filename

from backend.models import db, Patient, VcfFile

vcf_bp = Blueprint("vcf", __name__)

ALLOWED_VCF_EXTENSIONS = {".vcf", ".vcf.gz", ".bcf"}


def _allowed_vcf(filename: str) -> bool:
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in ALLOWED_VCF_EXTENSIONS)


@vcf_bp.route("/patients/<int:patient_id>/vcf", methods=["GET"])
def list_vcf_files(patient_id):
    """List all VCF files for a patient."""
    if not db.session.get(Patient, patient_id):
        abort(404)
    files = VcfFile.query.filter_by(patient_id=patient_id).all()
    return jsonify([f.to_dict() for f in files])


@vcf_bp.route("/patients/<int:patient_id>/vcf", methods=["POST"])
def upload_vcf(patient_id):
    """Upload a VCF file for a patient.

    The file is stored on disk under VCF_DIR/<lab_number>/.
    VCF_DIR can point to a local directory **or** a remote mount
    (NFS, SSHFS, S3-Fuse, etc.) — set the DATA_DIR / VCF_DIR
    environment variable on the server to redirect storage.
    """
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)

    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    f = request.files["file"]
    if not f.filename or not _allowed_vcf(f.filename):
        return jsonify({"error": "Invalid file type. Allowed: .vcf, .vcf.gz, .bcf"}), 400

    vcf_dir = current_app.config["VCF_DIR"]
    patient_dir = os.path.join(vcf_dir, patient.lab_number)
    os.makedirs(patient_dir, exist_ok=True)

    filename = secure_filename(f.filename)
    dest = os.path.join(patient_dir, filename)
    f.save(dest)

    relative_path = os.path.join(patient.lab_number, filename)
    file_size = os.path.getsize(dest)

    vcf_record = VcfFile(
        patient_id=patient_id,
        filename=filename,
        relative_path=relative_path,
        file_size=file_size,
    )
    db.session.add(vcf_record)
    db.session.commit()

    return jsonify(vcf_record.to_dict()), 201


@vcf_bp.route("/vcf_files/<int:vcf_id>", methods=["DELETE"])
def delete_vcf_file(vcf_id):
    """Remove a single VCF file (disk + DB)."""
    record = db.session.get(VcfFile, vcf_id)
    if not record:
        abort(404)
    vcf_dir = current_app.config["VCF_DIR"]
    disk_path = os.path.join(vcf_dir, record.relative_path)
    if os.path.isfile(disk_path):
        os.remove(disk_path)
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "VCF file deleted"}), 200
