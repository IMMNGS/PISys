"""Report generation routes — preview data and Word document download.

Ported from the legacy ``patient_info`` Flask app.  Functions such as
``create_word_document``, ``generate_table``, ``generate_table_qc``,
``get_test_description`` and ``get_summary_result`` live here.
"""

import io
import os
import re
import tempfile
from datetime import datetime
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from flask import Blueprint, abort, jsonify, request, send_file

from backend.models import db, Patient, Singleton, Trio, NgsQc
from backend.routes.helpers import _patient_to_dict

reports_bp = Blueprint("reports", __name__)

# ── Static text constants from backend.report_constants ──────────────
from backend.constants.report import (
    GENE_LIST,
    PANEL_DESCRIPTION,
    GENE_FOOTNOTE,
    METHODS_SECTIONS,
    DISCLAIMERS,
)


# ── Helper functions ─────────────────────────────────────────────────────

def _format_date(value):
    """Return a date string formatted as dd/mm/yyyy, or '' if unavailable."""
    if not value:
        return ""
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y")
        d = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(value)


def get_test_description(test_type):
    """Return the test description blurb."""
    base = (
        "In-house Immunological Disorders SuperPanel gene panel from WES was tested "
        "by next generation sequencing, and 554 genes were included in the panel test."
    )
    if test_type and test_type.lower() == "trio":
        return f"{base} Trio analysis was performed."
    return base


def _resolve_finding_type(patient, variant_model=None):
    """Resolve finding type letters (e.g. C/I/A/N) for a patient.

    Uses ``patient.type_of_findings`` when present; otherwise infers from
    reportable variants in the provided model, or both Singleton/Trio models
    if no model is given.
    """
    finding_type = (patient.type_of_findings or "").upper().strip()
    if finding_type:
        return finding_type

    if variant_model is not None:
        present_types = (
            db.session.query(variant_model.reportable_variant)
            .filter(variant_model.patient_id == patient.id)
            .filter(variant_model.reportable_variant.isnot(None))
            .filter(variant_model.reportable_variant.notin_(("", "-")))
            .distinct()
            .all()
        )
        return "".join(sorted({r[0].upper() for r in present_types if r[0]}))

    all_singletons = Singleton.query.filter(
        Singleton.patient_id == patient.id,
        Singleton.reportable_variant.isnot(None),
        Singleton.reportable_variant.notin_(("", "-")),
    ).all()
    all_trios = Trio.query.filter(
        Trio.patient_id == patient.id,
        Trio.reportable_variant.isnot(None),
        Trio.reportable_variant.notin_(("", "-")),
    ).all()
    present = {
        v.reportable_variant.upper()
        for v in (all_singletons + all_trios)
        if v.reportable_variant
    }
    return "".join(sorted(present))


def get_summary_result(patient):
    """Generate summary result text based on the finding type and variant data.

    Args:
        patient: Patient model instance.

    Returns:
        A summary string suitable for inclusion in the report.
    """
    finding_type = _resolve_finding_type(patient)

    if "C" in finding_type:
        # Look for confirmed variants in singletons and trios
        c_singletons = Singleton.query.filter_by(
            patient_id=patient.id, reportable_variant="C"
        ).all()
        c_trios = Trio.query.filter_by(
            patient_id=patient.id, reportable_variant="C"
        ).all()
        variants = c_singletons + c_trios
        if variants:
            gene_names = []
            comment = None
            for v in variants:
                if v.gene_names:
                    gene_names.append(v.gene_names)
                if comment is None:
                    raw = (
                        (v.second_review_comment or "")
                        or (v.reportable_variant or "")
                        or (v.classification or "")
                    )
                    raw = str(raw).strip()
                    if raw:
                        # collapse whitespace and cap length
                        raw = " ".join(raw.split())
                        comment = raw if len(raw) <= 120 else raw[:117] + "..."

            if len(gene_names) == 1:
                use_comment = comment or "likely pathogenic"
                return (
                    f"One {use_comment} variant was detected in the "
                    f"{gene_names[0]} gene."
                )
            elif len(gene_names) > 1:
                # keep the concise multi-gene wording
                return (
                    f"Likely pathogenic variants were detected in the "
                    f"{', '.join(gene_names)} genes."
                )
        return "No reportable variants found for this patient."

    if "A" in finding_type:
        return (
            "No disease-causing variant detected to fully account for the "
            "patient\u2019s phenotype. However, details on some additional "
            "findings have been included for reference."
        )

    if "I" in finding_type or "N" in finding_type:
        return (
            "No disease-causing variant detected to fully account for the "
            "patient\u2019s phenotype."
        )

    return "No confirmed variants found."


def _resolve_single_gene(patient):
    """Resolve one representative gene symbol for single-gene report.

    Priority:
    1) Confirmed (C) singleton/trio variants
    2) Any singleton/trio variant
    3) Empty string when unavailable
    """
    def _first_gene(raw_value):
        raw = (raw_value or "").strip()
        if not raw:
            return ""
        parts = re.split(r"[,;/]", raw)
        for part in parts:
            token = part.strip()
            if token:
                return token
        return raw

    confirmed_variants = Singleton.query.filter_by(
        patient_id=patient.id, reportable_variant="C"
    ).all() + Trio.query.filter_by(
        patient_id=patient.id, reportable_variant="C"
    ).all()
    for variant in confirmed_variants:
        gene = _first_gene(getattr(variant, "gene_names", ""))
        if gene:
            return gene

    all_variants = Singleton.query.filter_by(patient_id=patient.id).all() + Trio.query.filter_by(
        patient_id=patient.id
    ).all()
    for variant in all_variants:
        gene = _first_gene(getattr(variant, "gene_names", ""))
        if gene:
            return gene

    return ""


def _resolve_patient_by_lab(identifier: str):
    """Look up a patient by lab_number or im_lab_number.

    Tries an exact match on ``lab_number`` first, then falls back to
    ``im_lab_number``.  Returns the Patient or None.
    """
    if not identifier:
        return None
    patient = Patient.query.filter_by(lab_number=identifier).first()
    if patient:
        return patient
    return Patient.query.filter_by(im_lab_number=identifier).first()


def generate_table(doc, variants, include_inherited_from=False):
    """Insert a variant results table into a python-docx Document.

    Args:
        doc: python-docx Document instance.
        variants: list of Singleton or Trio model instances.
        include_inherited_from: if True, add an "Inherited From" column (trio).
    """
    from docx.shared import Pt, Inches

    # Create one 4-row x 7-column table per variant to match legacy `patient_info` layout.
    for v in variants:
        table = doc.add_table(rows=4, cols=7)
        table.style = "Table Grid"
        table.allow_autofit = False

        # Column widths similar to legacy implementation
        widths = [1.1, 1.6, 0.85, 0.9, 0.95, 0.65, 1.1]
        for i, width in enumerate(widths):
            table.columns[i].width = Inches(width)
        # Match legacy total table width used in `patient_info`
        try:
            table.width = Inches(16.0)
        except Exception:
            pass

        # Minimal paragraph formatting for all cells
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    paragraph.paragraph_format.space_before = Pt(0)
                    paragraph.paragraph_format.space_after = Pt(0)
                    paragraph.paragraph_format.left_indent = Inches(0.1)
                    paragraph.paragraph_format.right_indent = Inches(0.1)

        # Header row
        headers = [
            'Gene name/OMIM',
            'Transcript/\nVariant in HGVS Nomenclature',
            'Exon Location',
            'Genotype/Zygosity',
            'Inheritance',
            'Parent origin',
            'Classification',
        ]
        for i, hdr in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = hdr
            for run in cell.paragraphs[0].runs:
                run.bold = True

        # Row 2: main fields
        gene_names = v.gene_names or ""
        omim_val = v.omimid or v.omim_id or ""
        gene_col = f"{gene_names}*{omim_val}" if (gene_names or omim_val) else ""

        hgvs_c = v.hgvs_c or ""
        hgvs_p = v.hgvs_p or ""
        transcript_col = f"{hgvs_c}\n{hgvs_p}" if (hgvs_c or hgvs_p) else ""

        gene_region = v.gene_region_combined or ""
        exon_num = v.exon_number or ""
        exon_col = ""
        if gene_region:
            exon_col = gene_region[0].upper() + (gene_region[1:] if len(gene_region) > 1 else "")
        if exon_num:
            exon_col = (exon_col + ' ' if exon_col else '') + exon_num + ' of '

        row1_data = [
            gene_col,
            transcript_col,
            exon_col,
            v.zygosity or "",
            v.inheritance or "",
            'N/A' if not include_inherited_from else (v.inherited_from or ""),
            v.second_review_comment or v.classification or "",
        ]
        for i, val in enumerate(row1_data):
            table.cell(1, i).text = str(val) if val is not None else ''

        # Row 3: position headers (first 5 columns)
        position_headers = [
            '',
            'Position        REF/ALT',
            'Assembly',
            'SNP Identifier',
            'Phenotype',
        ]
        for i, hdr in enumerate(position_headers):
            cell = table.cell(2, i)
            cell.text = hdr
            if hdr:
                for run in cell.paragraphs[0].runs:
                    run.bold = True
        table.cell(2, 4).merge(table.cell(2, 5)).merge(table.cell(2, 6))

        # Row 4: position data
        position = v.chr_pos or ''
        ref_alt = v.ref_alt or ''
        rsid = v.rsid or ''

        phenotype = ''
        titles = (v.title or '').split(';') if v.title else []
        omim_ids = (v.omim_id or '').split(',') if v.omim_id else []
        if titles and omim_ids:
            tmp_text = '; '.join(
                f"{a.strip()} #{b.strip()}"
                for a, b in zip(titles, omim_ids)
                if a and b and a.strip() and b.strip()
            )
            phenotype = f"{tmp_text};" if tmp_text else ''

        position_data = [
            '',
            f"{position}\t{ref_alt}",
            'GRCh38',
            rsid,
            phenotype,
        ]
        for i, val in enumerate(position_data):
            table.cell(3, i).text = str(val) if val is not None else ''
        table.cell(3, 4).merge(table.cell(3, 5)).merge(table.cell(3, 6))

        set_table_font_size(table, 9, idx_rows=[1, 3], idx_cols=[3])

        doc.add_paragraph()


def set_table_border_color(table, color="FFFFFF"):
    """Set all borders of a table to a specific color."""
    tbl = table._element
    tbl_pr = tbl.tblPr

    tbl_borders = OxmlElement('w:tblBorders')
    tbl_pr.append(tbl_borders)

    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        border = tbl_borders.find(qn(f"w:{border_name}"))
        if border is None:
            border = OxmlElement(f"w:{border_name}")
            tbl_borders.append(border)
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color)


def set_table_font_size(table, size_pt, idx_rows=None, idx_cols=None):
    """Adjust run font size for selected table cells."""
    from docx.shared import Pt

    for i, row in enumerate(table.rows):
        if idx_rows is not None and i not in idx_rows:
            continue
        for j, cell in enumerate(row.cells):
            if idx_cols is not None and j not in idx_cols:
                continue
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(size_pt)


def generate_table_dmg(doc, patient):
    """Add patient header block table matching patient_info3 layout."""
    from docx.shared import Pt, Inches

    table = doc.add_table(rows=10, cols=2)
    table.style = "Table Grid"
    table.allow_autofit = False
    table.columns[0].width = Inches(2.5)
    table.columns[1].width = Inches(4)

    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                paragraph.paragraph_format.space_before = Pt(0.1)
                paragraph.paragraph_format.space_after = Pt(0.1)
                paragraph.paragraph_format.left_indent = Inches(0.1)
                paragraph.paragraph_format.right_indent = Inches(0.1)
        row.height = Inches(0.36)

    age_display = f"{patient.age or ''} {patient.age_unit or ''}".strip()
    row_data = [["REPORT DATE: ", _format_date(patient.report_date)]]
    info_pairs = [
        ("Lab. #", patient.im_lab_number or patient.lab_number or ""),
        ("Name", patient.name or ""),
        ("HKID", patient.hkid or ""),
        ("Date of Birth", _format_date(patient.dob)),
        ("Sex", patient.sex or ""),
        ("Age", age_display),
        ("Ethnicity", patient.ethnicity or ""),
        ("Specimen Collected", _format_date(patient.specimen_collected)),
        ("Specimen Arrived", _format_date(patient.specimen_arrived)),
    ]
    for label, value in info_pairs:
        row_data.append([f"{label}:", value])

    for idx, (k, v) in enumerate(row_data):
        key_cell = table.cell(idx, 0)
        key_cell.text = str(k) if k else ""
        if key_cell.paragraphs and key_cell.paragraphs[0].runs:
            key_cell.paragraphs[0].runs[0].bold = True

        val_cell = table.cell(idx, 1)
        val_cell.text = str(v) if v else ""
        if idx == 0 and val_cell.paragraphs and val_cell.paragraphs[0].runs:
            val_cell.paragraphs[0].runs[0].bold = True

    set_table_border_color(table, "FFFFFF")
    doc.add_paragraph()

def _fmt_qc_value(value, suffix=""):
    """Format a numeric QC value for the report table; '' when missing."""
    if value is None:
        return ""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if num.is_integer():
        text = f"{int(num)}"
    else:
        text = f"{num:.1f}"
    return text + suffix


def _latest_qc_for_patient(patient):
    """Return the most recent NgsQc row for a patient, or None."""
    if patient is None or getattr(patient, "id", None) is None:
        return None
    return (
        NgsQc.query
        .filter_by(patient_id=patient.id)
        .order_by(NgsQc.uploaded_at.desc())
        .first()
    )


def generate_table_qc(doc, patient=None):
        """Insert the Sequencing Performance Metrics QC table.

        Auto-fills the % >20X, Uniformity, and Median Coverage cells from
        the patient's most recent NgsQc record. Other cells (panel name,
        gene/exon/base counts) remain templated for now.
        """
        from docx.shared import Pt, Inches

        heading = doc.add_paragraph()
        heading.add_run("SEQUENCING PERFORMANCE METRICS").bold = True

        table = doc.add_table(rows=2, cols=7)
        table.style = "Table Grid"
        table.allow_autofit = False
        table.width = Inches(16.0)

        widths = [1.3, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0]
        for i, width in enumerate(widths):
            table.columns[i].width = Inches(width)

        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    paragraph.paragraph_format.space_before = Pt(0)
                    paragraph.paragraph_format.space_after = Pt(0)
                    paragraph.paragraph_format.left_indent = Inches(0.1)
                    paragraph.paragraph_format.right_indent = Inches(0.1)

        headers = [
            "PANELS", "GENES", "EXONS/\nREGIONS", "BASES",
            "% of target\nregion >20X", "Uniformity\n(%)", "MEDIAN\nCOVERAGE",
        ]
        for i, hdr in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = hdr
            for run in cell.paragraphs[0].runs:
                run.bold = True

        qc = _latest_qc_for_patient(patient)
        pct_20x_text = _fmt_qc_value(qc.pct_20x, "%") if qc else ""
        uniformity_text = _fmt_qc_value(qc.uniformity_pct, "%") if qc else ""
        median_cov_text = _fmt_qc_value(qc.median_coverage) if qc else ""

        row1_data = [
            "Immunological\nDisorders\nSuperPanel", "554", "15,798",
            "2,359,627",
            pct_20x_text,
            uniformity_text,
            median_cov_text,
        ]
        for i, val in enumerate(row1_data):
            table.cell(1, i).text = val

        doc.add_paragraph()

def create_word_document(
    patient,
    test_type="singleton",
    interpretation="",
    comments="",
    variant_classification="",
    test_process="",
    disclaimer="",
    references="",
):
        """Generate a full Word (.docx) report for a patient.

        Args:
            patient: Patient model instance (with relationships loaded).
            test_type: ``'singleton'`` or ``'trio'``.

        Returns:
            A BytesIO buffer containing the .docx file.
        """
        from docx import Document
        from docx.shared import Pt, Inches

        doc = Document()

        # Control document dimensions and styles
        section = doc.sections[0]
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(12)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        generate_table_dmg(doc, patient)

        # Separator
        p = doc.add_paragraph()
        p.add_run("-" * 117)

        # Add summary of results
        summary_sections = [
            ("SPECIMEN", "EDTA blood"),
            ("CLINICAL HISTORY", patient.clinical_history or ""),
            ("TYPE OF TESTING REQUESTED", patient.type_of_test or ""),
            ("TEST DESCRIPTION", test_process or get_test_description(test_type)),
            ("SUMMARY OF RESULT(S)", get_summary_result(patient)),
        ]
        for label, value in summary_sections:
            p = doc.add_paragraph()
            p.add_run(f"{label}:").bold = True
            p = doc.add_paragraph()
            run = p.add_run(str(value))
            if label == "SUMMARY OF RESULT(S)":
                run.bold = True

        # Variant table — confirmed (C) findings
        is_trio = test_type.lower() == "trio"
        VariantModel = Trio if is_trio else Singleton

        finding_type = _resolve_finding_type(patient, variant_model=VariantModel)

        c_variants = VariantModel.query.filter_by(
            patient_id=patient.id, reportable_variant="C"
        ).all()

        if c_variants:
            doc.add_page_break()
            p = doc.add_paragraph()
            p.add_run("RESULTS:").bold = True
            generate_table(doc, c_variants, include_inherited_from=is_trio)

        # Additional findings (A)
        a_variants = VariantModel.query.filter_by(
            patient_id=patient.id, reportable_variant="A"
        ).all()
        if a_variants:
            doc.add_page_break()
            p = doc.add_paragraph()
            p.add_run("Additional Findings:").bold = True
            generate_table(doc, a_variants, include_inherited_from=is_trio)

        # Interpretation text based on finding type
        if "A" in finding_type:
            p = doc.add_paragraph()
            p.add_run("INTERPRETATION / RECOMMENDED ACTION:").bold = True
            p = doc.add_paragraph()
            p.add_run(
                "Sequence analysis in current study with the Immunology gene panel did not "
                "detect any known disease-causing variants that could fully account the "
                "patient\u2019s phenotype as described to the laboratory at the time of "
                "interpretation. Please note that negative results do not rule out the "
                "diagnosis of a genetic disorder since some of the DNA abnormalities may be "
                "undetectable by the current applied technology. Further investigations may "
                "be considered if clinically indicated."
            )

        # Editable sections
        doc.add_page_break()
        editable_sections = [
            ("INTERPRETATION / RECOMMENDED ACTION:", interpretation),
            ("COMMENTS:", comments),
            ("VARIANT CLASSIFICATION:", variant_classification),
        ]
        for section_title, section_text in editable_sections:
            p = doc.add_paragraph()
            p.add_run(section_title).bold = True
            if section_text and str(section_text).strip():
                p = doc.add_paragraph()
                p.add_run(str(section_text).strip())
            else:
                for _ in range(6):
                    doc.add_paragraph()

        # Incidental findings (I)
        if ("I" in finding_type or "N" in finding_type) and "A" not in finding_type:
            p = doc.add_paragraph()
            p.add_run("INTERPRETATION / RECOMMENDED ACTION:").bold = True
            p = doc.add_paragraph()
            p.add_run(
                "Sequencing analysis in the current study did not detect any disease-causing "
                "variants that could fully account the patient\u2019s phenotypes as described "
                "to the laboratory at the time of interpretation."
            )
            p.add_run(
                "Please note that negative results do not rule out the diagnosis of a genetic "
                "disorder since some of the DNA abnormalities may be undetectable by the "
                "current applied technology. Moreover, variants assessment and interpretations "
                "may change with time when additional information from the patient\u2019s "
                "assessment or in the literature is available in the future. Test results "
                "should always be interpreted with clinical context, family history and other "
                "relevant data. Further investigations, such as whole exome / genome "
                "sequencing, assays targeting somatic mutation, CNV etc. may be considered if "
                "clinically indicated."
            )

        if "I" in finding_type or "N" in finding_type:
            p = doc.add_paragraph()
            run = p.add_run("APPENDIX")
            run.underline = True
            run.bold = True

        i_variants = VariantModel.query.filter_by(
            patient_id=patient.id, reportable_variant="I"
        ).all()
        if i_variants:
            doc.add_page_break()
            p = doc.add_paragraph()
            p.add_run(
                "SUMMARY LIST OF OTHER INCIDENTAL FINDINGS WITHIN THE PANEL:"
            ).bold = True
            generate_table(doc, i_variants, include_inherited_from=is_trio)

        # QC table
        generate_table_qc(doc, patient)

        # Target region and gene list page
        doc.add_page_break()

        p = doc.add_paragraph()
        p.add_run("TARGET REGION AND GENE LIST").bold = True
        doc.add_paragraph()

        # Add gene list and footnote with smaller font size
        p = doc.add_paragraph()
        run = p.add_run(GENE_LIST)
        run.font.size = Pt(9)

        doc.add_paragraph()
        p = doc.add_paragraph()
        run = p.add_run(GENE_FOOTNOTE)
        run.font.size = Pt(9)

        p = doc.add_paragraph()
        run = p.add_run(PANEL_DESCRIPTION)
        run.font.size = Pt(9)

        # Methods
        p = doc.add_paragraph()
        p.add_run("METHODS:").bold = True
        doc.add_paragraph()

        method_items = [
            ("Laboratory process:", METHODS_SECTIONS["laboratory_process"]),
            ("Bioinformatics and quality control:", METHODS_SECTIONS["bioinformatics"]),
            ("Interpretation:", METHODS_SECTIONS["interpretation"]),
            ("Variant classification:", METHODS_SECTIONS["variant_classification"]),
            ("Databases:", METHODS_SECTIONS["databases"]),
            ("Confirmation of sequence alterations:", METHODS_SECTIONS["confirmation"]),
            ("Analytic validation:", METHODS_SECTIONS["validation"]),
            ("Assay limitations:", METHODS_SECTIONS["limitations"]),
        ]
        for subtitle, text in method_items:
            p = doc.add_paragraph()
            run = p.add_run(subtitle)
            run.underline = True
            p.add_run(" " + text)

        doc.add_paragraph(
            "Further test details could be found at Division\u2019s webpage: "
            "https://hkwc.home/webapps/Dept/CIMM/CellFnMolecularImmLab.aspx"
        )

        # Disclaimers
        p = doc.add_paragraph()
        p.add_run("DISCLAIMERS:").bold = True
        disclaimer_lines = []
        if disclaimer and str(disclaimer).strip():
            disclaimer_lines = [ln.strip() for ln in str(disclaimer).splitlines() if ln.strip()]
        if not disclaimer_lines:
            disclaimer_lines = list(DISCLAIMERS)
        for i, disclaimer_line in enumerate(disclaimer_lines, 1):
            doc.add_paragraph(f"({i}) {disclaimer_line}")

        if references and str(references).strip():
            p = doc.add_paragraph()
            p.add_run("REFERENCES:").bold = True
            doc.add_paragraph(str(references).strip())

        # Signatures
        doc.add_paragraph()
        doc.add_paragraph("Reported By:")
        doc.add_paragraph()
        doc.add_paragraph("Dr. Edmund Tung")
        doc.add_paragraph()
        doc.add_paragraph("Signed Out By:")
        doc.add_paragraph()
        doc.add_paragraph("Consultant Immunologist")
        doc.add_paragraph("Dr. Au Yuen Ling Elaine")
        doc.add_paragraph()
        doc.add_paragraph("********** End of report **********")

        # Write to buffer
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf


def create_single_gene_word_document(patient):
    """Generate a minimal single-gene style Word (.docx) report.

    Args:
        patient: Patient model instance.

    Returns:
        A BytesIO buffer containing the .docx file.
    """
    from docx import Document
    from docx.shared import Pt

    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(12)
    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    age_display = str(patient.age or "")
    if patient.age_unit:
        age_display = f"{age_display} {patient.age_unit}".strip()

    single_gene = _resolve_single_gene(patient)

    title_pairs = [
        ("REPORT DATE:", _format_date(patient.report_date)),
        ("LAB#:", patient.im_lab_number or patient.lab_number or ""),
        ("NAME:", patient.name or ""),
        ("HKID:", patient.hkid or ""),
        ("SEX / AGE:", f"{patient.sex or ''} / {age_display}".strip(" /")),
        ("DOB:", _format_date(patient.dob)),
        ("SPECIMEN COLLECTED:", _format_date(patient.specimen_collected)),
        ("SPECIMEN ARRIVED:", _format_date(patient.specimen_arrived)),
        ("ETHNICITY:", patient.ethnicity or ""),
        ("SINGLE GENE:", single_gene or "N/A"),
    ]

    for label, value in title_pairs:
        p = doc.add_paragraph()
        p.alignment = 1
        run = p.add_run(f"{label} {value}".rstrip())
        run.bold = label == "REPORT DATE:"

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ── API routes ───────────────────────────────────────────────────────────

@reports_bp.route("/report/preview", methods=["POST"])
def report_preview():
    """Return data needed to preview a report in the frontend.

    Body: ``{ "lab_number": "...", "test_type": "singleton"|"trio" }``

    Returns patient data, variant list, and default text blocks that can be
    edited in the UI before final generation.
    """
    data = request.get_json()
    lab_number = (data.get("lab_number") or "").strip()
    test_type = (data.get("test_type") or "singleton").lower()

    if not lab_number:
        return jsonify({"error": "lab_number is required"}), 400

    patient = _resolve_patient_by_lab(lab_number)
    if not patient:
        return jsonify({"error": f"No patient with lab_number '{lab_number}'"}), 404

    # Fetch variants for this patient
    if test_type == "trio":
        variants_q = Trio.query.filter_by(patient_id=patient.id)
    else:
        variants_q = Singleton.query.filter_by(patient_id=patient.id)
    variants = variants_q.order_by("id").all()

    return jsonify({
        "patient": _patient_to_dict(
            patient, include_hpo=True,
            include_singletons=True, include_trios=True,
            include_vcf_files=True,
        ),
        "variants": [v.to_dict() for v in variants],
        "defaults": {
            "test_process": get_test_description(test_type),
            "disclaimer": "\n".join(f"({i}) {d}" for i, d in enumerate(DISCLAIMERS, 1)),
            "references": (
                "IUSI expert committee: Journal of clinical immunology vol. 40,1 "
                "(2020): 24-64, J Hum Immun 5 May 2025; 1(1):e20250002"
            ),
        },
    })


@reports_bp.route("/report/generate", methods=["POST"])
def generate_report():
    """Generate and download a Word (.docx) report for a patient.

    Body: ``{ "lab_number": "...", "test_type": "singleton"|"trio",
              "conclusion": "...", "test_process": "...",
              "disclaimer": "...", "references": "..." }``

    Returns: the .docx file as an attachment.
    """
    data = request.get_json()
    lab_number = (data.get("lab_number") or "").strip()
    test_type = (data.get("test_type") or "singleton").lower()
    interpretation = (data.get("interpretation") or data.get("conclusion") or "").strip()
    comments = (data.get("comments") or "").strip()
    variant_classification = (data.get("variant_classification") or "").strip()
    test_process = (data.get("test_process") or "").strip()
    disclaimer = (data.get("disclaimer") or "").strip()
    references = (data.get("references") or "").strip()

    if not lab_number:
        return jsonify({"error": "lab_number is required"}), 400

    patient = _resolve_patient_by_lab(lab_number)
    if not patient:
        return jsonify({"error": f"No patient with lab_number '{lab_number}'"}), 404

    try:
        buf = create_word_document(
            patient,
            test_type=test_type,
            interpretation=interpretation,
            comments=comments,
            variant_classification=variant_classification,
            test_process=test_process,
            disclaimer=disclaimer,
            references=references,
        )
    except ImportError:
        return jsonify({
            "error": "python-docx is not installed. Run: pip install python-docx"
        }), 500
    except Exception as e:
        return jsonify({"error": f"Report generation failed: {str(e)}"}), 500

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Keep filename format aligned with legacy patient_info3 output.
    filename = f"patient_info_{patient.im_lab_number or patient.lab_number}_{timestamp}.docx"

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )


@reports_bp.route("/report/generate-single-gene", methods=["POST"])
@reports_bp.route("/generate_single_gene_report", methods=["POST"])
def generate_single_gene_report():
    """Generate and download a minimal single-gene Word (.docx) report.

    Accepts JSON body or form-encoded body with ``lab_number``.
    """
    payload = request.get_json(silent=True) or request.form
    lab_number = (payload.get("lab_number") or "").strip()

    if not lab_number:
        return jsonify({"error": "lab_number is required"}), 400

    patient = _resolve_patient_by_lab(lab_number)
    if not patient:
        return jsonify({"error": f"No patient with lab_number '{lab_number}'"}), 404

    try:
        buf = create_single_gene_word_document(patient)
    except ImportError:
        return jsonify({
            "error": "python-docx is not installed. Run: pip install python-docx"
        }), 500
    except Exception as e:
        return jsonify({"error": f"Single-gene report generation failed: {str(e)}"}), 500

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"single_gene_report_{patient.im_lab_number or patient.lab_number}_{timestamp}.docx"

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )
