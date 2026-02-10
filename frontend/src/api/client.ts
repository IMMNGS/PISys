import type {
  HPOTermPage,
  PatientInfo,
  SingletonInfo,
  TrioInfo,
  VcfFileInfo,
} from "../types";

const BASE = "/api";

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
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

// ── Patients ─────────────────────────────────────────────────────────────

export function fetchPatients(search = ""): Promise<PatientInfo[]> {
  const params = new URLSearchParams({ search });
  return json(`${BASE}/patients?${params}`);
}

export function fetchPatient(id: number): Promise<PatientInfo> {
  return json(`${BASE}/patients/${id}`);
}

export function fetchSelectedPatients(ids: number[]): Promise<PatientInfo[]> {
  return json(`${BASE}/patients/selected`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_ids: ids }),
  });
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
  const res = await fetch(`${BASE}/patients/${patientId}/vcf`, {
    method: "POST",
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
  const res = await fetch(`${BASE}/patients/${patientId}/upload/singleton`, {
    method: "POST",
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
  const res = await fetch(`${BASE}/patients/${patientId}/upload/trio`, {
    method: "POST",
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
  const res = await fetch(`${BASE}/report/preview`, {
    method: "POST",
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
  conclusion: string;
  test_process: string;
  disclaimer: string;
  references: string;
}): Promise<void> {
  const res = await fetch(`${BASE}/report/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { error?: string }).error || `${res.status} ${res.statusText}`,
    );
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `report_${params.lab_number}.docx`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Bulk Patient Import ──────────────────────────────────────────────────

export async function uploadPatientsXlsx(
  file: File,
): Promise<{ message: string; added: number; skipped: string[] }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/patients/upload`, {
    method: "POST",
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
