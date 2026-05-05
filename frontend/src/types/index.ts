// ── Domain types ─────────────────────────────────────────────────────────

export interface HPOTerm {
  id: number;
  hpo_id: string;
  term_name: string;
  definition: string | null;
  synonyms: string | null;
}

export interface DiseaseTerm {
  id: number;
  term_name: string;
  normalized_name?: string;
  notes?: string | null;
  created_at?: string | null;
}

export interface SingletonInfo {
  id: number;
  patient_id: number;
  reportable_variant: string | null;
  chr_pos: string | null;
  ref_alt: string | null;
  igv_review: boolean | null;
  second_review_comment: string | null;
  gene_names: string | null;
  hgvs_c: string | null;
  hgvs_p: string | null;
  exon_number: string | null;
  zygosity: string | null;
  inheritance: string | null;
  inherited_from: string | null;
  classification: string | null;
  omim_id: string | null;
  rsid: string | null;
  title: string | null;
  omimid: string | null;
  gene_region_combined: string | null;
  created_at: string | null;
}

export interface TrioInfo {
  id: number;
  patient_id: number;
  reportable_variant: string | null;
  chr_pos: string | null;
  ref_alt: string | null;
  igv_review: boolean | null;
  second_review_comment: string | null;
  gene_names: string | null;
  hgvs_c: string | null;
  hgvs_p: string | null;
  exon_number: string | null;
  zygosity: string | null;
  inheritance: string | null;
  inherited_from: string | null;
  classification: string | null;
  omim_id: string | null;
  rsid: string | null;
  title: string | null;
  omimid: string | null;
  gene_region_combined: string | null;
  created_at: string | null;
}

export interface VariantUploadInfo {
  id: number;
  patient_id: number;
  file_type: string;
  original_filename: string;
  stored_filename: string;
  relative_path: string;
  file_size: number | null;
  uploaded_at: string | null;
}

export interface VcfFileInfo {
  id: number;
  patient_id: number;
  filename: string;
  relative_path: string;
  file_size: number | null;
  uploaded_at: string | null;
}

export interface PatientInfo {
  id: number;
  report_date: string | null;
  lab_number: string;
  im_lab_number: string | null;
  name: string | null;
  hkid: string | null;
  dob: string | null;
  sex: string | null;
  age: string | number | null;
  age_unit: string | null;
  ethnicity: string | null;
  specimen_collected: string | null;
  specimen_arrived: string | null;
  clinical_history?: string | null;
  case_history?: string | null;
  type_of_test: string | null;
  type_of_findings: string | null;
  findings_summary: string | null;
  ngs_batch: string | null;
  ngs_tat: string | null;
  ngs_tat_final: string | null;
  request_dr: string | null;
  remark: string | null;
  created_at: string | null;
  hpo_terms: HPOTerm[];
  disease_terms?: DiseaseTerm[];
  singletons?: SingletonInfo[];
  trios?: TrioInfo[];
  vcf_files?: VcfFileInfo[];
  variant_uploads?: VariantUploadInfo[];
}

export type QcType = "panel" | "exome";

export interface NgsQcInfo {
  id: number;
  patient_id: number | null;
  sample_label: string | null;
  is_control: boolean;
  qc_type: QcType;
  batch: string | null;
  median_coverage: number | null;
  pct_20x: number | null;
  uniformity_pct: number | null;
  pass_fail: string | null;
  notes: string | null;
  metrics: Record<string, string>;
  positive_control: Record<string, string>;
  original_filename: string | null;
  relative_path: string | null;
  file_size: number | null;
  uploaded_at: string | null;
}

export interface QcBulkUploadResult {
  batch: string | null;
  qc_type: QcType;
  filename: string;
  positive_control_label: string;
  positive_control: Record<string, string>;
  matched_count: number;
  control_count: number;
  unmatched: string[];
  records: NgsQcInfo[];
  control_records: NgsQcInfo[];
}

export interface NgsQcBatchInfo {
  id: number;
  qc_type: QcType;
  batch: string | null;
  positive_control_label: string | null;
  positive_control: Record<string, string>;
  original_filename: string | null;
  relative_path: string | null;
  file_size: number | null;
  uploaded_at: string | null;
  matched_count: number;
  unmatched_labels: string[];
}

export interface QcRecordWithPatient extends NgsQcInfo {
  patient_lab_number: string | null;
  patient_im_lab_number: string | null;
  patient_name: string | null;
}

export interface QcStats {
  averages: {
    median_coverage: number | null;
    pct_20x: number | null;
    uniformity_pct: number | null;
  };
  pass_fail: {
    pass: number;
    fail: number;
    borderline: number;
    total: number;
  };
  batch_summaries: {
    batch: string;
    qc_type: string;
    avg_median_coverage: number | null;
    avg_pct_20x: number | null;
    avg_uniformity_pct: number | null;
    record_count: number;
  }[];
}

export interface VariantAuditEntry {
  id: number;
  patient_id: number | null;
  variant_type: "singleton" | "trio";
  variant_id: number;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  changed_by: string;
  changed_at: string | null;
}

export interface HPOTermPage {
  items: HPOTerm[];
  total: number;
  page: number;
  pages: number;
}
