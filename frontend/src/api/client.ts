import type {
  HPOTermPage,
  HPOTerm,
  DiseaseTerm,
  PatientInfo,
  SingletonInfo,
  TrioInfo,
  VcfFileInfo,
} from "../types";

const BASE = "/api";

let csrfToken = "";

export function setCsrfToken(token: string | null | undefined) {
  csrfToken = token || "";
}

function needsCsrf(method?: string) {
  const verb = (method || "GET").toUpperCase();
  return !["GET", "HEAD", "OPTIONS"].includes(verb);
}

function withCsrf(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers || {});
  if (needsCsrf(init?.method) && csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  return {
    ...init,
    headers,
  };
}

async function request(url: string, init?: RequestInit) {
  return fetch(url, {
    credentials: "include",
    ...withCsrf(init),
    cache: "no-store" as RequestCache,
  });
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await request(url, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export interface AuthUser {
  id: number;
  username: string;
  full_name: string | null;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string | null;
  last_login_at: string | null;
}

export interface AuthSessionResponse {
  authenticated: boolean;
  user: AuthUser | null;
  csrf_token: string;
}

export interface AuditLogItem {
  id: number;
  user_id: number | null;
  username: string;
  action: string;
  target: string;
  method: string;
  path: string;
  status_code: number;
  remote_addr: string | null;
  user_agent: string | null;
  created_at: string | null;
}

export function fetchSession(): Promise<AuthSessionResponse> {
  return json<AuthSessionResponse>(`${BASE}/auth/me`).then((session) => {
    setCsrfToken(session.csrf_token);
    return session;
  });
}

export function login(
  username: string,
  password: string,
): Promise<AuthSessionResponse> {
  return json<AuthSessionResponse>(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  }).then((session) => {
    setCsrfToken(session.csrf_token);
    return session;
  });
}

export function logout(): Promise<{ message: string }> {
  return json<{ message: string; csrf_token: string }>(`${BASE}/auth/logout`, {
    method: "POST",
  }).then((result) => {
    setCsrfToken(result.csrf_token);
    return { message: result.message };
  });
}

export function fetchAuditLogs(
  params: {
    limit?: number;
    offset?: number;
    username?: string;
    action?: string;
    target?: string;
  } = {},
): Promise<{ items: AuditLogItem[]; total: number }> {
  const search = new URLSearchParams();
  if (params.limit != null) search.set("limit", String(params.limit));
  if (params.offset != null) search.set("offset", String(params.offset));
  if (params.username) search.set("username", params.username);
  if (params.action) search.set("action", params.action);
  if (params.target) search.set("target", params.target);
  const suffix = search.toString() ? `?${search}` : "";
  return json(`${BASE}/admin/audit-logs${suffix}`);
}

export function fetchUsers(): Promise<{ items: AuthUser[] }> {
  return json(`${BASE}/admin/users`);
}

export function createUser(payload: {
  username: string;
  password: string;
  role?: "admin" | "user";
  full_name?: string;
}): Promise<{ message: string; user: AuthUser }> {
  return json(`${BASE}/admin/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ── HPO Terms ────────────────────────────────────────────────────────────

export function fetchHPOTerms(
  search = "",
  page = 1,
  perPage = 50,
): Promise<HPOTermPage> {
  const params = new URLSearchParams({
    search,
    page: String(page),
    per_page: String(perPage),
  });
  return json(`${BASE}/hpo_terms?${params}`);
}

export function refreshHPOTerms(): Promise<{
  message: string;
  added: number;
  updated: number;
  error?: string;
}> {
  return json(`${BASE}/hpo_terms/refresh`, { method: "POST" });
}

export interface HPOOption {
  id: number;
  hpo_id: string;
  term_name: string;
}

export interface CombinedTermOption {
  id: number;
  term_type: "hpo" | "disease";
  term_id: number;
  hpo_id?: string;
  term_name: string;
  label: string;
}

export function fetchHPOOptions(
  search = "",
  limit = 20,
  offset = 0,
): Promise<PaginatedOptions<HPOOption>> {
  const params = new URLSearchParams({
    search,
    limit: String(limit),
    offset: String(offset),
  });
  return json(`${BASE}/hpo_terms/options?${params}`);
}

export function fetchHPOTermById(termId: number): Promise<HPOTerm> {
  return json(`${BASE}/hpo_terms/${termId}`);
}

export function fetchCombinedTermOptions(
  search = "",
  limit = 20,
  offset = 0,
): Promise<PaginatedOptions<CombinedTermOption>> {
  const params = new URLSearchParams({
    search,
    limit: String(limit),
    offset: String(offset),
  });
  return json(`${BASE}/terms/options?${params}`);
}

export function fetchDiseaseTerms(
  search = "",
  page = 1,
  perPage = 50,
): Promise<{
  items: DiseaseTerm[];
  total: number;
  page: number;
  pages: number;
}> {
  const params = new URLSearchParams({
    search,
    page: String(page),
    per_page: String(perPage),
  });
  return json(`${BASE}/disease_terms?${params}`);
}

export interface DiseaseTermOption {
  id: number;
  term_name: string;
}

export function fetchDiseaseTermOptions(
  search = "",
  limit = 20,
  offset = 0,
): Promise<PaginatedOptions<DiseaseTermOption>> {
  const params = new URLSearchParams({
    search,
    limit: String(limit),
    offset: String(offset),
  });
  return json(`${BASE}/disease_terms/options?${params}`);
}

export function fetchDiseaseTermById(termId: number): Promise<DiseaseTerm> {
  return json(`${BASE}/disease_terms/${termId}`);
}

export async function updateDiseaseTerm(
  termId: number,
  payload: { term_name?: string; notes?: string },
): Promise<DiseaseTerm> {
  const res = await request(`${BASE}/disease_terms/${termId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  return res.json();
}

export function deleteDiseaseTerm(
  termId: number,
): Promise<{ message: string }> {
  return json(`${BASE}/disease_terms/${termId}`, { method: "DELETE" });
}

export function upsertFreeTextTerm(
  termName: string,
  notes?: string,
): Promise<{
  id: number;
  term_id: number;
  term_type: "disease";
  label: string;
}> {
  return json(`${BASE}/terms/free_text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ term_name: termName, notes }),
  });
}

// ── Patients ─────────────────────────────────────────────────────────────

export function fetchPatients(search = ""): Promise<PatientInfo[]> {
  const params = new URLSearchParams({ search });
  return json(`${BASE}/patients?${params}`);
}

export interface PatientOption {
  id: number;
  lab_number: string;
  im_lab_number: string | null;
  name: string | null;
}

export interface PaginatedOptions<T> {
  items: T[];
  total: number;
}

export function fetchPatientOptions(
  search = "",
  limit = 20,
  offset = 0,
): Promise<PaginatedOptions<PatientOption>> {
  const params = new URLSearchParams({
    search,
    limit: String(limit),
    offset: String(offset),
  });
  return json(`${BASE}/patients/options?${params}`);
}

export interface PatientListFilters {
  lab_number?: string;
  im_lab_number?: string;
  name?: string;
  sex?: string;
  age?: string;
  type_of_test?: string;
  term_ids?: string;
}

export interface CreatePatientPayload {
  lab_number: string;
  im_lab_number?: string;
  name?: string;
  hkid?: string;
  report_date?: string;
  dob?: string;
  sex?: string;
  age?: string;
  age_unit?: string;
  ethnicity?: string;
  specimen_collected?: string;
  specimen_arrived?: string;
  case_history?: string;
  clinical_history?: string;
  type_of_test?: string;
  type_of_findings?: string;
  findings_summary?: string;
  ngs_batch?: string;
  ngs_tat?: string;
  ngs_tat_final?: string;
  request_dr?: string;
  remark?: string;
}

export function fetchPatientList(
  filters: PatientListFilters = {},
  limit = 20,
  offset = 0,
): Promise<PaginatedOptions<PatientInfo>> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  for (const [k, v] of Object.entries(filters)) {
    if (v) params.set(k, v);
  }
  return json(`${BASE}/patients/list?${params}`);
}

export interface FilterOptions {
  sex: string[];
  type_of_test: string[];
  terms: {
    id: number;
    term_type: "hpo" | "disease";
    term_name: string;
    hpo_id?: string;
    label: string;
  }[];
}

export interface InsightCountSummary {
  patients: number;
  singleton_variants: number;
  trio_variants: number;
  total_variants: number;
  vcf_files: number;
  vcf_content_variants: number;
  vcf_files_readable: number;
  vcf_files_skipped: number;
}

export interface CountByChromosome {
  chromosome: string;
  count: number;
}

export interface CountByVariant {
  variant: string;
  count: number;
}

export interface CountByGene {
  gene: string;
  count: number;
  chromosome?: string | null;
}

export interface CountByTerm {
  term_type: "hpo" | "disease";
  term: string;
  count: number;
}

export interface CountByLabel {
  label: string;
  count: number;
}

export interface VcfPatientVariantSummary {
  patient_id: number;
  lab_number: string;
  file_count: number;
  variant_count: number;
}

export interface SampleVariantCount {
  patient_id: number;
  lab_number: string;
  singleton_count: number;
  trio_count: number;
  total_count: number;
}

export interface InsightSummaryResponse {
  counts: InsightCountSummary;
  demographic_distribution: {
    sex: CountByLabel[];
    age: CountByLabel[];
    ethnicity: CountByLabel[];
    test_type: CountByLabel[];
  };
  vcf_distribution: {
    file_size: CountByLabel[];
  };
  vcf_content_distribution: {
    chromosome: CountByChromosome[];
    variant_type: CountByLabel[];
    by_patient: VcfPatientVariantSummary[];
  };
  chromosome_distribution: CountByChromosome[];
  reported_variant_distribution: CountByLabel[];
  sample_variant_counts: SampleVariantCount[];
  top_variants: CountByVariant[];
  top_genes: CountByGene[];
  top_terms: CountByTerm[];
}

export interface ExplainResponse {
  kind: string;
  query: string;
  explanation: string;
  source: string;
  medical_disclaimer?: string;
  citations?: Array<{
    type: string;
    label: string;
    fields: Record<string, unknown>;
  }>;
  matched?: {
    hpo_id: string;
    term_name: string;
  };
  details?: {
    synonyms?: string;
  };
}

export function fetchInsightSummary(
  params: {
    start_date?: string;
    end_date?: string;
    test_type?: string;
  } = {},
): Promise<InsightSummaryResponse> {
  const search = new URLSearchParams();
  if (params.start_date) search.set("start_date", params.start_date);
  if (params.end_date) search.set("end_date", params.end_date);
  if (params.test_type) search.set("test_type", params.test_type);
  const suffix = search.toString() ? `?${search}` : "";
  return json(`${BASE}/insights/summary${suffix}`);
}

export async function explainEntity(
  kind: "hpo" | "variant" | "text",
  query: string,
  includeCitations = true,
): Promise<ExplainResponse> {
  const res = await request(`${BASE}/insights/explain`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, query, include_citations: includeCitations }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  return res.json();
}

export function fetchFilterOptions(): Promise<FilterOptions> {
  return json(`${BASE}/patients/filter_options`);
}

export function fetchPatient(id: number): Promise<PatientInfo> {
  return json(`${BASE}/patients/${id}`);
}

export async function createPatient(
  payload: CreatePatientPayload,
): Promise<PatientInfo> {
  const res = await request(`${BASE}/patients`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  return res.json();
}

export function updatePatient(
  patientId: number,
  data: Partial<PatientInfo>,
): Promise<PatientInfo> {
  return json(`${BASE}/patients/${patientId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function deletePatient(patientId: number): Promise<{ message: string }> {
  return json(`${BASE}/patients/${patientId}`, { method: "DELETE" });
}

export function fetchSelectedPatients(ids: number[]): Promise<PatientInfo[]> {
  return json(`${BASE}/patients/selected`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_ids: ids }),
  });
}

export type ExtractionMode = "selected_files" | "all_files";
export type ExtractionFileType = "singletons" | "trios" | "vcf_files";

export function extractSelectedPatients(
  ids: number[],
  mode: ExtractionMode,
  fileTypes: ExtractionFileType[] = [],
): Promise<PatientInfo[]> {
  return json(`${BASE}/patients/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_ids: ids,
      mode,
      file_types: fileTypes,
    }),
  });
}

export async function downloadCommonVariantsVcf(ids: number[]): Promise<void> {
  const res = await request(`${BASE}/patients/extract/common_variants_vcf`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_ids: ids }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }

  const disposition = res.headers.get("Content-Disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
  const downloadName = filenameMatch ? filenameMatch[1] : "common_variants.vcf";

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = downloadName;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Assign / Remove HPO ──────────────────────────────────────────────────

export function assignHPO(
  patientIds: number[],
  hpoTermIds: number[],
): Promise<{ message: string }> {
  return json(`${BASE}/patients/assign_hpo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_ids: patientIds, hpo_term_ids: hpoTermIds }),
  });
}

export function assignTerms(
  patientIds: number[],
  termIds: number[],
): Promise<{ message: string; hpo_added: number; disease_added: number }> {
  return json(`${BASE}/patients/assign_terms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_ids: patientIds, term_ids: termIds }),
  });
}

export function assignDiseaseTerms(
  patientIds: number[],
  diseaseTermIds: number[],
): Promise<{ message: string }> {
  return json(`${BASE}/patients/assign_disease_terms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_ids: patientIds,
      disease_term_ids: diseaseTermIds,
    }),
  });
}

export function removeTerms(
  patientIds: number[],
  termIds: number[],
): Promise<{ message: string; hpo_removed: number; disease_removed: number }> {
  return json(`${BASE}/patients/remove_terms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_ids: patientIds, term_ids: termIds }),
  });
}

export function removeDiseaseTerms(
  patientIds: number[],
  diseaseTermIds: number[],
): Promise<{ message: string }> {
  return json(`${BASE}/patients/remove_disease_terms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_ids: patientIds,
      disease_term_ids: diseaseTermIds,
    }),
  });
}

export function fetchPatientDiseaseTerms(
  patientId: number,
): Promise<DiseaseTerm[]> {
  return json(`${BASE}/patients/${patientId}/disease_terms`);
}

export function removePatientDiseaseTerm(
  patientId: number,
  termId: number,
): Promise<{ message: string }> {
  return json(`${BASE}/patients/${patientId}/disease_terms/${termId}`, {
    method: "DELETE",
  });
}

export function removeHPO(
  patientId: number,
  termId: number,
): Promise<{ message: string }> {
  return json(`${BASE}/patients/${patientId}/hpo_terms/${termId}`, {
    method: "DELETE",
  });
}

// ── Singletons ───────────────────────────────────────────────────────────

export function fetchSingletons(patientId: number): Promise<SingletonInfo[]> {
  return json(`${BASE}/patients/${patientId}/singletons`);
}

export function createSingleton(
  patientId: number,
  data: Partial<SingletonInfo>,
): Promise<SingletonInfo> {
  return json(`${BASE}/patients/${patientId}/singletons`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function updateSingleton(
  singletonId: number,
  data: Partial<SingletonInfo>,
): Promise<SingletonInfo> {
  return json(`${BASE}/singletons/${singletonId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function deleteSingleton(
  singletonId: number,
): Promise<{ message: string }> {
  return json(`${BASE}/singletons/${singletonId}`, {
    method: "DELETE",
  });
}

// ── Trios ────────────────────────────────────────────────────────────────

export function updateTrio(
  trioId: number,
  data: Partial<TrioInfo>,
): Promise<TrioInfo> {
  return json(`${BASE}/trios/${trioId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// ── VCF Files ────────────────────────────────────────────────────────────

export function fetchVcfFiles(patientId: number): Promise<VcfFileInfo[]> {
  return json(`${BASE}/patients/${patientId}/vcf`);
}

export async function uploadVcfFile(
  patientId: number,
  file: File,
): Promise<VcfFileInfo> {
  const form = new FormData();
  form.append("file", file);
  const res = await request(`${BASE}/patients/${patientId}/vcf`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  return res.json();
}

export function deleteVcfFile(vcfId: number): Promise<{ message: string }> {
  return json(`${BASE}/vcf_files/${vcfId}`, { method: "DELETE" });
}

// ── XLSX Import (Singleton / Trio) ───────────────────────────────────────

export async function uploadSingletonXlsx(
  patientId: number,
  file: File,
): Promise<{ message: string; count: number }> {
  const form = new FormData();
  form.append("file", file);
  const res = await request(`${BASE}/patients/${patientId}/upload/singleton`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  return res.json();
}

export async function uploadTrioXlsx(
  patientId: number,
  file: File,
): Promise<{ message: string; count: number }> {
  const form = new FormData();
  form.append("file", file);
  const res = await request(`${BASE}/patients/${patientId}/upload/trio`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  return res.json();
}

// ── Report Generation ────────────────────────────────────────────────────

export interface ReportPreview {
  patient: PatientInfo;
  variants: (SingletonInfo | TrioInfo)[];
  defaults: {
    test_process: string;
    disclaimer: string;
    references: string;
  };
}

export async function fetchReportPreview(
  labNumber: string,
  testType: "singleton" | "trio",
): Promise<ReportPreview> {
  const res = await request(`${BASE}/report/preview`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lab_number: labNumber, test_type: testType }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  return res.json();
}

export async function downloadReport(params: {
  lab_number: string;
  test_type: "singleton" | "trio";
  interpretation?: string;
  comments?: string;
  variant_classification?: string;
  conclusion?: string;
  test_process: string;
  disclaimer: string;
  references: string;
}): Promise<void> {
  const res = await request(`${BASE}/report/generate`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  // Extract filename from Content-Disposition header if available
  const disposition = res.headers.get("Content-Disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
  const downloadName = filenameMatch
    ? filenameMatch[1]
    : `patient_info_${params.lab_number}.docx`;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = downloadName;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadSingleGeneReport(
  labNumber: string,
): Promise<void> {
  const res = await request(`${BASE}/report/generate-single-gene`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lab_number: labNumber }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }

  const disposition = res.headers.get("Content-Disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
  const downloadName = filenameMatch
    ? filenameMatch[1]
    : `single_gene_report_${labNumber}.docx`;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = downloadName;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Bulk Patient Import ──────────────────────────────────────────────────

export async function uploadPatientsXlsx(
  file: File,
): Promise<{ message: string; added: number; skipped: string[] }> {
  const form = new FormData();
  form.append("file", file);
  const res = await request(`${BASE}/patients/upload`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  return res.json();
}
