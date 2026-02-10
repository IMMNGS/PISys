"""Report preview and .docx generation routes."""

from flask import Blueprint, jsonify, request

from backend.models import db, Patient, Singleton, Trio

reports_bp = Blueprint("reports", __name__)

DEFAULT_TEST_PROCESS = (
    "DNA was extracted from the specimen. Massively parallel sequencing was "
    "performed on a panel of 32 genes (details available in laboratory website: "
    "https://......). Bioinformatic analysis to detect single nucleotide and indel variants "
    "was performed using an in-house pipeline (Leukaemia Panel Pipeline Version: v1.8.1). "
    "Sequence reads were aligned to Human Genome Assembly GRCh38/hg38. Analytical "
    "sensitivity has been established at 5% variant allele frequency. Variants are reported "
    "in accordance with AMP/ASCO/CAP classification system."
)

DEFAULT_DISCLAIMER = (
    "This test aims at detecting single nucleotide variants (SNVs) and short indels that are "
    "located in exons and splice sites (encompassing the -10 position at the splice acceptor "
    "site and +10 position at the splice donor site) of targeted genes. It does not detect "
    "all variants in the non-targeted genomic regions and variants in the noncoding regions "
    "and copy number variants. Structural variants are not analysed. The analytical "
    "sensitivity of the test may be compromised in genomic regions with sequence related to "
    "highly homologous genes, pseudogenes or repetitive elements.\n"
    "This test detects both germline cancer predisposition variants and clinically "
    "actionable somatic variants in haematological malignancies. When paired germline sample "
    "is not tested, this test does not allow definitive differentiation between germline and "
    "somatic variants. The clinical significance of some reported variants may be different "
    "should they be determined as germline variants with a paired germline sample at a later "
    "time."
)

DEFAULT_REFERENCES = "Döhner H et al. Blood 2022;140:1345-1377."


@reports_bp.route("/report/preview", methods=["POST"])
def preview_report():
    """Return the data that will populate the report, so the frontend can show
    an editable preview before generating the .docx."""
    data = request.get_json(force=True)
    lab_number = data.get("lab_number", "").strip()
    test_type = data.get("test_type", "singleton")

    if not lab_number:
        return jsonify({"error": "lab_number is required"}), 400

    patient = Patient.query.filter_by(lab_number=lab_number).first()
    if not patient:
        return jsonify({"error": f"No patient with lab_number '{lab_number}'"}), 404

    if test_type == "trio":
        variants = [t.to_dict() for t in Trio.query.filter_by(patient_id=patient.id).all()]
    else:
        variants = [s.to_dict() for s in Singleton.query.filter_by(patient_id=patient.id).all()]

    return jsonify({
        "patient": patient.to_dict(include_hpo=False, include_singletons=False,
                                   include_trios=False, include_vcf_files=False),
        "variants": variants,
        "defaults": {
            "test_process": DEFAULT_TEST_PROCESS,
            "disclaimer": DEFAULT_DISCLAIMER,
            "references": DEFAULT_REFERENCES,
        },
    })


@reports_bp.route("/report/generate", methods=["POST"])
def generate_report():
    """Generate a .docx patient report matching the clinical template.

    POST JSON body:
      lab_number (str)          – required
      test_type  (str)          – "singleton" or "trio"
      conclusion (str)          – free-text conclusion paragraph
      test_process (str)        – editable test-process paragraph
      disclaimer (str)          – editable disclaimer paragraph
      references (str)          – editable references text
    """
    from docx import Document
    from docx.shared import Pt
    from docx.enum.table import WD_TABLE_ALIGNMENT
    import io

    data = request.get_json(force=True)
    lab_number = data.get("lab_number", "").strip()
    test_type = data.get("test_type", "singleton")
    conclusion_text = data.get("conclusion", "").strip()
    test_process_text = data.get("test_process", "").strip()
    disclaimer_text = data.get("disclaimer", "").strip()
    references_text = data.get("references", "").strip()

    if not lab_number:
        return jsonify({"error": "lab_number is required"}), 400

    patient = Patient.query.filter_by(lab_number=lab_number).first()
    if not patient:
        return jsonify({"error": f"No patient with lab_number '{lab_number}'"}), 404

    # Fetch variants
    if test_type == "trio":
        variants = Trio.query.filter_by(patient_id=patient.id).all()
    else:
        variants = Singleton.query.filter_by(patient_id=patient.id).all()

    # ── Build .docx ──────────────────────────────────────────────

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10)

    # Helper: add bold label paragraph
    def add_bold_line(label, value):
        p = doc.add_paragraph()
        run = p.add_run(f"{label}: ")
        run.bold = True
        run.font.size = Pt(10)
        p.add_run(str(value) if value else "—").font.size = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(0)
        return p

    def add_section_heading(text):
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(11)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        return p

    # ── Patient Identity ─────────────────────────────────────────
    age_str = ""
    if patient.age is not None:
        unit = (patient.age_unit or "Y").upper()
        if unit.startswith("Y"):
            age_str = f"{patient.age}Y"
        elif unit.startswith("M"):
            age_str = f"{patient.age}M"
        elif unit.startswith("D"):
            age_str = f"{patient.age}D"
        else:
            age_str = f"{patient.age}{unit}"
    sex_age = f"{patient.sex or '—'}/{age_str}" if age_str else (patient.sex or "—")

    add_bold_line("Name", patient.name or "—")
    add_bold_line("Sex/Age", sex_age)
    add_bold_line("HKID", patient.hkid or "—")

    # ── Testing Information ──────────────────────────────────────
    add_section_heading("Testing Information:")
    test_fields = [
        ("Case History", patient.case_history),
        ("Type of Test", patient.type_of_test),
        ("Specimen Collected", str(patient.specimen_collected) if patient.specimen_collected else None),
    ]
    for label, val in test_fields:
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").font.size = Pt(10)
        p.add_run(str(val) if val else "—").font.size = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(0)

    # ── Result table ─────────────────────────────────────────────
    add_section_heading("Result:")
    cols = ["Gene Name/OMIM", "Transcript / Variant (HGVS)", "Exon",
            "Zygosity", "Inheritance", "Parent Origin",
            "Classification", "Position REF/ALT", "Assembly",
            "SNP Identifier", "Phenotype"]
    table = doc.add_table(rows=1, cols=len(cols))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Light Grid Accent 1"

    # Header row
    hdr = table.rows[0]
    for i, col in enumerate(cols):
        cell = hdr.cells[i]
        cell.text = col
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(8)

    # Data rows
    for v in variants:
        row = table.add_row()
        gene_omim = v.gene_names or "—"
        if v.omim_id:
            gene_omim += f" / {v.omim_id}"
        row.cells[0].text = gene_omim
        hgvs = ""
        if v.hgvs_c:
            hgvs = v.hgvs_c
        if v.hgvs_p:
            hgvs += f" ({v.hgvs_p})" if hgvs else v.hgvs_p
        row.cells[1].text = hgvs or "—"
        row.cells[2].text = v.exon_number or "—"
        row.cells[3].text = v.zygosity or "—"
        row.cells[4].text = v.inheritance or "—"
        row.cells[5].text = v.inherited_from or "—"
        row.cells[6].text = v.classification or "—"
        pos_ref_alt = ""
        if v.chr_pos:
            pos_ref_alt = v.chr_pos
        if v.ref_alt:
            pos_ref_alt += f" {v.ref_alt}" if pos_ref_alt else v.ref_alt
        row.cells[7].text = pos_ref_alt or "—"
        row.cells[8].text = "GRCh38/hg38"
        row.cells[9].text = v.rsid or "—"
        row.cells[10].text = v.title or "—"
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(8)

    # ── Conclusion ───────────────────────────────────────────────
    add_section_heading("Conclusion:")
    p = doc.add_paragraph(conclusion_text or "—")
    p.style.font.size = Pt(10)

    # ── Test Process ─────────────────────────────────────────────
    add_section_heading("Test Process:")
    p = doc.add_paragraph(test_process_text or "—")
    p.style.font.size = Pt(10)

    # ── Disclaimer ───────────────────────────────────────────────
    add_section_heading("Disclaimer:")
    for para_text in (disclaimer_text or "—").split("\n"):
        p = doc.add_paragraph(para_text.strip())
        p.style.font.size = Pt(10)

    # ── References ───────────────────────────────────────────────
    add_section_heading("References:")
    p = doc.add_paragraph(references_text or "—")
    p.style.font.size = Pt(10)

    # ── Write & return ───────────────────────────────────────────
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    from flask import send_file
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=f"report_{patient.lab_number}.docx",
    )
