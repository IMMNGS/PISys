"""Shared helpers and constants used across route modules."""

import math
import re
from difflib import SequenceMatcher


def _patient_to_dict(patient, include_hpo=True, include_singletons=False,
                     include_trios=False, include_vcf_files=False,
                     include_disease_terms=False):
    """Serialize a patient."""
    return patient.to_dict(
        include_hpo=include_hpo,
        include_singletons=include_singletons,
        include_trios=include_trios,
        include_vcf_files=include_vcf_files,
        include_disease_terms=include_disease_terms,
    )


def _parse_xlsx_rows(file_storage):
    """Read an XLSX file from a FileStorage object and return list of dicts.

    Automatically maps Excel column names to database field names using
    fuzzy matching against known column name variations.
    """
    import openpyxl

    wb = openpyxl.load_workbook(file_storage, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    def _row_headers(row):
        return [str(h).strip() if h else f"col_{i}" for i, h in enumerate(row)]

    def _choose_header_index(all_rows):
        """Pick the most likely patient header row from the first few rows."""
        available = get_available_patient_fields()
        best_idx = 0
        best_score = float("-inf")
        scan_limit = min(6, len(all_rows))

        for idx in range(scan_limit):
            row = all_rows[idx]
            headers = _row_headers(row)
            mapping = auto_map_columns(headers, available)
            mapped_fields = set(mapping.values())

            # Prefer rows that look like real headers and map key fields.
            text_cells = sum(1 for v in row if isinstance(v, str) and v.strip())
            non_empty_cells = sum(1 for v in row if v is not None and str(v).strip())
            score = (len(mapping) * 10) + (text_cells * 2) + non_empty_cells
            if "lab_number" in mapped_fields:
                score += 30
            if "name" in mapped_fields:
                score += 8
            if "im_lab_number" in mapped_fields:
                score += 5

            if score > best_score:
                best_score = score
                best_idx = idx

        return best_idx

    header_idx = _choose_header_index(rows)
    raw_headers = _row_headers(rows[header_idx])

    # Try auto-mapping first, fall back to simple lowercased names
    available = get_available_patient_fields()
    mapping = auto_map_columns(raw_headers, available)

    headers = []
    for h in raw_headers:
        if h in mapping:
            headers.append(mapping[h])
        else:
            headers.append(h.lower().replace(" ", "_"))

    result = []
    for row in rows[header_idx + 1:]:
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in row):
            continue
        d = {}
        for h, v in zip(headers, row):
            d[h] = v
        result.append(d)
    return result


def _parse_variant_xlsx_rows(file_storage):
    """Read a singleton/trio variant XLSX file and return a list of dicts.

    Handles the specific column names used in variant spreadsheets with fuzzy
    matching against known column name variations.
    """
    import openpyxl

    wb = openpyxl.load_workbook(file_storage, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    # The variant files typically have header on row 2 (index 1),
    # try both row 0 and row 1
    raw_headers_row0 = rows[0]
    raw_headers_row1 = rows[1] if len(rows) > 2 else None

    # Decide which row is the header by checking if row 0 looks like data
    # (i.e. has mostly None values or numeric-looking values)
    def _looks_like_header(row):
        str_count = sum(1 for v in row if isinstance(v, str) and len(v) > 1)
        return str_count >= 3

    # Check both rows and see which one maps to more variant columns
    row0_headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(raw_headers_row0)]
    row1_headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(raw_headers_row1)] if raw_headers_row1 else []

    map0 = auto_map_variant_columns(row0_headers)
    map1 = auto_map_variant_columns(row1_headers) if row1_headers else {}

    section_metadata = {}
    
    if len(map1) > len(map0) and len(map1) >= 3:
        raw_headers = row1_headers
        data_start = 2
        # Extract section metadata from row 0
        current_section = None
        valid_cols = 0
        for i, val in enumerate(raw_headers_row0):
            if val and isinstance(val, str) and val.strip():
                current_section = val.strip()
            
            if current_section:
                lower_sec = current_section.lower()
                is_data_section = (
                    "variant" in lower_sec or
                    "im" in lower_sec or
                    "proband" in lower_sec or
                    "mother" in lower_sec or
                    "father" in lower_sec or
                    "lab" in lower_sec
                )
                if not is_data_section:
                    break
                
                section_metadata[i] = current_section
            valid_cols += 1
            
        raw_headers = raw_headers[:valid_cols]
    elif len(map0) > 0 and len(map0) >= len(map1):
        raw_headers = row0_headers
        data_start = 1
    elif _looks_like_header(raw_headers_row0):
        raw_headers = row0_headers
        data_start = 1
    elif raw_headers_row1 and _looks_like_header(raw_headers_row1):
        raw_headers = row1_headers
        data_start = 2
        # Extract section metadata from row 0
        current_section = None
        valid_cols = 0
        for i, val in enumerate(raw_headers_row0):
            if val and isinstance(val, str) and val.strip():
                current_section = val.strip()
            
            if current_section:
                lower_sec = current_section.lower()
                is_data_section = (
                    "variant" in lower_sec or
                    "im" in lower_sec or
                    "proband" in lower_sec or
                    "mother" in lower_sec or
                    "father" in lower_sec or
                    "lab" in lower_sec
                )
                if not is_data_section:
                    break
                
                section_metadata[i] = current_section
            valid_cols += 1
            
        raw_headers = raw_headers[:valid_cols]
    else:
        raw_headers = row0_headers
        data_start = 1

    # Map variant-specific column names to DB field names
    mapping = auto_map_variant_columns(raw_headers)

    headers = []
    for h in raw_headers:
        if h in mapping:
            headers.append(mapping[h])
        else:
            headers.append(h)

    result = []
    for row in rows[data_start:]:
        d = {}
        for i, (h, v) in enumerate(zip(headers, row)):
            sec = section_metadata.get(i)
            # Create a unique key if this header already exists in d
            key = h
            if key in d:
                if sec:
                    # Prefix with section if possible
                    proposed = f"{sec}_{h}"
                    # Ensure proposed is also unique
                    suffix = 1
                    while proposed in d:
                        proposed = f"{sec}_{h}_{suffix}"
                        suffix += 1
                    key = proposed
                else:
                    # Make it unique by adding suffix
                    suffix = 1
                    proposed = f"{h}_{suffix}"
                    while proposed in d:
                        suffix += 1
                        proposed = f"{h}_{suffix}"
                    key = proposed
            
            # If we have a section but it's not a standard mapped field, 
            # and it's not already in d, let's prefix it to be safe,
            # so custom columns reflect their section. (Optional, but user said "for singleton another section that is needed is the lab number")
            if sec and h not in mapping.values() and key == h:
                key = f"{sec}_{h}"

            d[key] = v
        result.append(d)
    return result


def _normalize_variant_field(field, value):
    """Normalize a single variant field value before DB persistence."""
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    if field == "igv_review":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            text = value.strip().lower()
            if not text:
                return None
            if text in {"true", "1", "yes", "y", "t"}:
                return True
            if text in {"false", "0", "no", "n", "f"}:
                return False
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if field == "reportable_variant":
            return value.upper()
        return value

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value).strip() or None


def normalize_variant_row(row, fields):
    """Normalize a parsed variant row to canonical DB-ready values."""
    normalized = {}
    for field in fields:
        val = row.get(field)
        val = _normalize_variant_field(field, val)
        if val is not None:
            normalized[field] = val

    # Legacy files may provide OMIM in either column; keep both populated.
    if normalized.get("omim_id") and not normalized.get("omimid"):
        normalized["omimid"] = normalized["omim_id"]
    elif normalized.get("omimid") and not normalized.get("omim_id"):
        normalized["omim_id"] = normalized["omimid"]

    # Deduplicate and truncate omimid and omim_id to fit in 50 chars
    for omim_field in ["omim_id", "omimid"]:
        if normalized.get(omim_field):
            # Split by comma, strip whitespace, remove empty, and deduplicate while maintaining order
            parts = [p.strip() for p in normalized[omim_field].split(",") if p.strip()]
            seen = set()
            deduped = [p for p in parts if not (p in seen or seen.add(p))]
            joined = ",".join(deduped)
            normalized[omim_field] = joined[:50]

    return normalized


# ── Field definitions ────────────────────────────────────────────────────

PATIENT_FIELDS = (
    "lab_number", "im_lab_number", "name", "hkid", "dob", "sex", "age",
    "age_unit", "ethnicity", "specimen_collected", "specimen_arrived",
    "case_history", "clinical_history", "type_of_test", "type_of_findings", "findings_summary",
    "ngs_batch", "ngs_tat", "ngs_tat_final", "request_dr", "remark",
    "report_date",
)

SINGLETON_FIELDS = (
    "reportable_variant", "chr_pos", "ref_alt", "igv_review",
    "second_review_comment", "gene_names", "hgvs_c", "hgvs_p", "exon_number",
    "zygosity", "inheritance", "inherited_from", "classification",
    "omim_id", "rsid", "title", "omimid", "gene_region_combined",
)

TRIO_FIELDS = (
    "reportable_variant", "chr_pos", "ref_alt", "igv_review",
    "second_review_comment", "gene_names", "hgvs_c", "hgvs_p", "exon_number",
    "zygosity", "inheritance", "inherited_from", "classification",
    "omim_id", "rsid", "title", "omimid", "gene_region_combined",
)

DATE_FIELDS = {"dob", "report_date", "specimen_collected", "specimen_arrived"}


# ── Validation helpers ───────────────────────────────────────────────────

def validate_lab_number(lab_number):
    """Validate the lab number format.

    Returns True if the format is valid (IMxxx or 2-char+2-char+digits), False
    otherwise.
    """
    if not lab_number or not isinstance(lab_number, str):
        return False
    im_pattern = r'^IM\d{3,6}$'
    num_pattern = r'^\d{2}\w{2}\d{3,6}$'
    return bool(re.match(im_pattern, lab_number) or re.match(num_pattern, lab_number))


# ── Auto-mapping helpers ─────────────────────────────────────────────────

def get_available_patient_fields():
    """Return the canonical set of patient DB fields with human-readable labels.

    This is the single source of truth for patient field definitions.
    """
    return {
        "lab_number": "Lab Number (Required)",
        "im_lab_number": "IM Lab Number",
        "name": "Patient Name",
        "hkid": "HKID",
        "dob": "Date of Birth",
        "sex": "Sex/Gender",
        "age": "Age",
        "age_unit": "Age Unit",
        "ethnicity": "Ethnicity",
        "specimen_collected": "Specimen Collected Date",
        "specimen_arrived": "Specimen Arrived Date",
        "report_date": "Report Date",
        "case_history": "Case History",
        "type_of_test": "Type of Test",
        "type_of_findings": "Type of Findings",
        "ngs_batch": "NGS Batch",
        "ngs_tat": "NGS TAT",
        "ngs_tat_final": "NGS TAT Final",
        "request_dr": "Requesting Doctor",
        "remark": "Remarks",
    }


# Known variations of Excel column names → DB field name
_PATIENT_FIELD_VARIATIONS = {
    "lab_number": [
        "Lab. no.", "Request_No", "lab number", "lab_number", "lab. no.",
        "lab. no", "lab no", "labno", "lab#", "specimen id", "sample id",
    ],
    "im_lab_number": [
        "IM Lab. no.", "im lab number", "im_lab_number", "im lab. no.",
        "im lab. no", "im lab no", "im lab#", "im number",
    ],
    "name": [
        "Patient name", "Name", "patient name", "name", "patient",
        "full name", "surname", "patient surname",
    ],
    "hkid": ["HKID", "hkid", "hk id", "id number", "identification", "id"],
    "dob": ["date of birth", "dob", "birth date", "date birth", "birthday"],
    "sex": ["Sex", "sex", "gender", "sex/gender", "male/female"],
    "age": ["Age", "age", "patient age"],
    "age_unit": ["Age unit", "Age_unit", "age unit", "age_unit", "age units"],
    "ethnicity": ["ethnicity", "ethnic", "ethnicity/race"],
    "specimen_collected": [
        "Sample collection date", "Collected_Date", "specimen collected",
        "specimen_collected", "sample collected", "collection date",
        "collected date", "sample collection date",
    ],
    "specimen_arrived": [
        "Sample receive date", "Arrived_Date", "specimen arrived",
        "specimen_arrived", "sample arrived", "arrival date",
        "arrived date", "sample receive date",
    ],
    "report_date": ["report date", "report_date", "reported date", "reporting date"],
    "case_history": [
        "Case", "case history", "Clinical_Detail", "case_history",
        "clinical history", "clinical_history", "history", "diagnosis",
    ],
    "type_of_test": [
        "type of test", "type_of_test", "test type", "test_type", "testing type",
    ],
    "type_of_findings": [
        "type of findings", "type_of_findings", "findings", "finding type",
        "finding_type", "result type",
    ],
    "request_dr": [
        "Requesting Dr.", "requesting doctor", "request_dr",
        "requesting dr", "requesting physician", "Request Dr.", "Request Dr. ",
    ],
    "ngs_tat": [
        "NGS TAT", "NGS TAT Wet + Dry (56 days)", "ngs tat",
        "ngs turnaround time", "ngs_turnaround_time", "TAT for NGS",
    ],
    "ngs_tat_final": [
        "NGS TAT Final", "NGS final TAT (84 days)", "ngs tat final",
        "ngs turnaround time final", "ngs_turnaround_time_final",
    ],
    "ngs_batch": ["NGS Batch", "NGS Batch no.", "ngs batch", "ngs_batch"],
    "remark": ["Remark", "Remarks", "remarks", "note", "notes", "comments"],
}


def auto_map_columns(excel_columns, available_fields):
    """Automatically map Excel column names to database field names.

    Uses exact matching, case-insensitive matching, and fuzzy matching.

    Args:
        excel_columns: List of column names from the Excel file.
        available_fields: Dict of available database fields (from
            ``get_available_patient_fields``).

    Returns:
        Dict mapping Excel column names to database field names.
    """
    mapping = {}
    used_fields = set()

    # First pass: exact and case-insensitive matches
    for excel_col in excel_columns:
        excel_col_lower = excel_col.lower().strip()
        for db_field, variations in _PATIENT_FIELD_VARIATIONS.items():
            if db_field in used_fields:
                continue
            for variation in variations:
                if excel_col_lower == variation.lower():
                    mapping[excel_col] = db_field
                    used_fields.add(db_field)
                    break
            if excel_col in mapping:
                break

    # Second pass: fuzzy matching for unmapped columns
    for excel_col in excel_columns:
        if excel_col in mapping:
            continue
        excel_col_lower = excel_col.lower().strip()
        best_match = None
        best_ratio = 0.6  # minimum similarity threshold

        for db_field, variations in _PATIENT_FIELD_VARIATIONS.items():
            if db_field in used_fields:
                continue
            for variation in variations:
                ratio = SequenceMatcher(
                    None, excel_col_lower, variation.lower()
                ).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = db_field

        if best_match:
            mapping[excel_col] = best_match
            used_fields.add(best_match)

    return mapping


# Known variations of variant Excel column names → DB field name
_VARIANT_FIELD_VARIATIONS = {
    "reportable_variant": [
        "Reportable Variant", "reportable variant", "reportable_variant",
    ],
    "chr_pos": ["Chr:Pos", "chr:pos", "chr_pos", "chromosome position"],
    "ref_alt": ["Ref/Alt", "ref/alt", "ref_alt"],
    "igv_review": [
        "IGV review ( True / False call)", "IGV review",
        "igv review", "igv_review",
    ],
    "second_review_comment": [
        "Second review and comment on reportable variant ",
        "Second review and comment on reportable variant",
        "Second review and comment", "second_review_comment",
    ],
    "gene_names": ["Gene Names", "gene names", "gene_names", "gene name"],
    "hgvs_c": [
        "HGVS c. (Clinically Relevant)", "HGVS c.", "hgvs_c", "hgvs c",
    ],
    "hgvs_p": [
        "HGVS p. (Clinically Relevant)", "HGVS p.", "hgvs_p", "hgvs p",
    ],
    "gene_region_combined": [
        "Gene Region (Combined)", "gene region", "gene_region_combined",
    ],
    "exon_number": [
        "Exon Number (Clinically Relevant)", "Exon Number",
        "exon_number", "exon number",
    ],
    "zygosity": ["Zygosity", "zygosity"],
    "inheritance": ["Inheritance", "inheritance"],
    "inherited_from": ["Inherited From", "inherited from", "inherited_from"],
    "classification": ["Classification", "classification"],
    "omimid": ["OMIMID", "OMIM ID.1", "omimid"],
    "omim_id": ["OMIM ID", "omim_id", "omim id"],
    "rsid": ["RSID", "rsid", "rs id"],
    "title": ["Title", "title"],
}


def auto_map_variant_columns(excel_columns):
    """Map variant XLSX column names to DB field names.

    Returns:
        Dict mapping Excel column names to DB field names.
    """
    mapping = {}
    used_fields = set()

    for excel_col in excel_columns:
        excel_col_lower = excel_col.lower().strip()
        for db_field, variations in _VARIANT_FIELD_VARIATIONS.items():
            if db_field in used_fields:
                continue
            for variation in variations:
                if excel_col_lower == variation.lower().strip():
                    mapping[excel_col] = db_field
                    used_fields.add(db_field)
                    break
            if excel_col in mapping:
                break

    # Fuzzy fallback
    for excel_col in excel_columns:
        if excel_col in mapping:
            continue
        excel_col_lower = excel_col.lower().strip()
        best_match = None
        best_ratio = 0.6
        for db_field, variations in _VARIANT_FIELD_VARIATIONS.items():
            if db_field in used_fields:
                continue
            for variation in variations:
                ratio = SequenceMatcher(
                    None, excel_col_lower, variation.lower()
                ).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = db_field
        if best_match:
            mapping[excel_col] = best_match
            used_fields.add(best_match)

    return mapping
