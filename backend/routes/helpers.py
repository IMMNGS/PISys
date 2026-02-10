"""Shared helpers and constants used across route modules."""


def _patient_to_dict(patient, include_hpo=True, include_singletons=False,
                     include_trios=False, include_vcf_files=False):
    """Serialize a patient."""
    return patient.to_dict(
        include_hpo=include_hpo,
        include_singletons=include_singletons,
        include_trios=include_trios,
        include_vcf_files=include_vcf_files,
    )


def _parse_xlsx_rows(file_storage):
    """Read an XLSX file from a FileStorage object and return list of dicts."""
    import openpyxl

    wb = openpyxl.load_workbook(file_storage, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []
    headers = [str(h).strip().lower().replace(" ", "_") if h else f"col_{i}"
               for i, h in enumerate(rows[0])]
    result = []
    for row in rows[1:]:
        d = {}
        for h, v in zip(headers, row):
            d[h] = v
        result.append(d)
    return result


PATIENT_FIELDS = (
    "lab_number", "im_lab_number", "name", "hkid", "dob", "sex", "age",
    "age_unit", "ethnicity", "specimen_collected", "specimen_arrived",
    "case_history", "type_of_test", "type_of_findings", "findings_summary",
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
