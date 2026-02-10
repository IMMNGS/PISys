// ── Domain types ─────────────────────────────────────────────────────────

export interface HPOTerm {
  id: number;
  hpo_id: string;
  term_name: string;
  definition: string | null;
  synonyms: string | null;
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
  age: number | null;
  age_unit: string | null;
  ethnicity: string | null;
  specimen_collected: string | null;
  specimen_arrived: string | null;
  case_history: string | null;
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
  singletons?: SingletonInfo[];
  trios?: TrioInfo[];
  vcf_files?: VcfFileInfo[];
}

export interface HPOTermPage {
  items: HPOTerm[];
  total: number;
  page: number;
  pages: number;
}
