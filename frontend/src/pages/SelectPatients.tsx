import { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import {
  fetchPatientList,
  extractSelectedPatients,
  downloadCommonVariantsVcf,
  fetchFilterOptions,
  fetchCombinedTermOptions,
  createPatient,
  deletePatient,
  uploadPatientsXlsx,
} from "../api/client";
import type { PatientInfo } from "../types";
import type { PatientListFilters, FilterOptions } from "../api/client";
import DropdownSelect from "../components/DropdownSelect";
import type { DropdownItem } from "../components/DropdownSelect";
import SearchableMultiSelect from "../components/SearchableMultiSelect";

/* ── Tab definitions for the code-guide panel ─────────────────────────── */
type ToolTab = "python" | "r" | "curl" | "sql";
type AddPatientMode = "manual" | "upload";
type ExtractMode = "selected_files" | "all_files" | "common_variants";

const TAB_LABELS: Record<ToolTab, string> = {
  python: "Python",
  r: "R",
  curl: "cURL / REST",
  sql: "SQL (direct)",
};

function codeBlock(ids: number[], baseUrl: string, tab: ToolTab): string {
  const idList = ids.join(", ");

  switch (tab) {
    case "python":
      return `import requests
import pandas as pd

# If connecting from a remote device, replace with the server's
# IP / hostname, e.g. "http://192.168.1.50:5001"
BASE_URL = "${baseUrl}"

# 1. Fetch selected patients
res = requests.post(
    f"{BASE_URL}/api/patients/selected",
    json={"patient_ids": [${idList}]},
)
res.raise_for_status()
patients = res.json()

# 2. Load into a DataFrame
df = pd.json_normalize(patients)
print(df.head())

# 3. Fetch singletons for one patient
pid = ${ids[0] ?? 1}
singletons = requests.get(f"{BASE_URL}/api/patients/{pid}/singletons").json()
df_sing = pd.DataFrame(singletons)

# 4. Fetch trio variants for one patient
trios = requests.get(f"{BASE_URL}/api/patients/{pid}/trios").json()
df_trio = pd.DataFrame(trios)

# 5. Fetch VCF file list for one patient
vcf_files = requests.get(f"{BASE_URL}/api/patients/{pid}/vcf").json()
print(vcf_files)
`;

    case "r":
      return `library(httr2)
library(jsonlite)

# If connecting from a remote device, replace with the server's
# IP / hostname, e.g. "http://192.168.1.50:5001"
base_url <- "${baseUrl}"

# 1. Fetch selected patients
resp <- request(paste0(base_url, "/api/patients/selected")) |>
  req_method("POST") |>
  req_body_json(list(patient_ids = c(${idList}))) |>
  req_perform()

patients <- resp |> resp_body_json(simplifyVector = TRUE)
print(head(patients))

# 2. Fetch singletons for one patient
pid <- ${ids[0] ?? 1}
singletons <- fromJSON(
  content(GET(paste0(base_url, "/api/patients/", pid, "/singletons")), "text")
)

# 3. Fetch trio variants for one patient
trios <- fromJSON(
  content(GET(paste0(base_url, "/api/patients/", pid, "/trios")), "text")
)

# 4. Fetch VCF file list for one patient
vcf_files <- fromJSON(
  content(GET(paste0(base_url, "/api/patients/", pid, "/vcf")), "text")
)
`;

    case "curl":
      return `# If connecting from a remote device, replace localhost
# with the server's IP / hostname.

# Fetch selected patients
curl -X POST ${baseUrl}/api/patients/selected \\
  -H "Content-Type: application/json" \\
  -d '{"patient_ids": [${idList}]}'

# Fetch all patients (with search)
curl "${baseUrl}/api/patients?search="

# Fetch singletons for a patient
curl ${baseUrl}/api/patients/${ids[0] ?? 1}/singletons

# Fetch trio variants for a patient
curl ${baseUrl}/api/patients/${ids[0] ?? 1}/trios

# Fetch VCF file list for a patient
curl ${baseUrl}/api/patients/${ids[0] ?? 1}/vcf

# Fetch disease terms for a patient
curl ${baseUrl}/api/patients/${ids[0] ?? 1}
`;

    case "sql":
      return `-- Connect to the patient_info database directly
-- (requires network access to the MySQL server)

-- Selected patients
SELECT * FROM patients
WHERE id IN (${idList});

-- Their singleton findings
SELECT s.* FROM singleton s
WHERE s.patient_id IN (${idList});

-- Their trio findings
SELECT t.* FROM trio t
WHERE t.patient_id IN (${idList});

-- Their VCF files
SELECT v.* FROM vcf_files v
WHERE v.patient_id IN (${idList});

-- Patients with disease terms
SELECT p.lab_number, p.name, h.hpo_id AS term_code, h.term_name
FROM patients p
JOIN patient_hpo ph ON ph.patient_id = p.id
JOIN hpo_terms h ON h.id = ph.hpo_term_id
WHERE p.id IN (${idList})
UNION ALL
SELECT p.lab_number, p.name, NULL AS term_code, d.term_name
FROM patients p
JOIN patient_disease_term pdt ON pdt.patient_id = p.id
JOIN disease_terms d ON d.id = pdt.disease_term_id
WHERE p.id IN (${idList});
`;
  }
}

/* ── Column-level filters ─────────────────────────────────────────────── */
interface Filters {
  lab_number: string;
  im_lab_number: string;
  name: string;
  sex: string;
  age: string;
  type_of_test: string;
  term_ids: string;
}

const emptyFilters: Filters = {
  lab_number: "",
  im_lab_number: "",
  name: "",
  sex: "",
  age: "",
  type_of_test: "",
  term_ids: "",
};

const PAGE_SIZE = 20;
const LOAD_MORE_SIZE = 100;
const FINDING_OPTIONS = ["", "C", "I", "A", "N", "C+I", "C+A", "I+A", "C+I+A"];

function isValidLabNumber(labNumber: string): boolean {
  const s = (labNumber || "").trim();
  return /^IM\d{3,6}$/.test(s) || /^\d{2}\w{2}\d{3,6}$/.test(s);
}

function trimOrUndefined(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function displayPatientId(
  patient: Pick<PatientInfo, "lab_number" | "im_lab_number">,
): string {
  const im = (patient.im_lab_number || "").trim();
  return im || patient.lab_number;
}

/* ── Component ────────────────────────────────────────────────────────── */
export default function SelectPatients() {
  const [patients, setPatients] = useState<PatientInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [results, setResults] = useState<PatientInfo[] | null>(null);
  const [activeTab, setActiveTab] = useState<ToolTab>("python");
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [actionMsg, setActionMsg] = useState<{
    type: "success" | "error";
    msg: string;
  } | null>(null);
  const [showAddPatient, setShowAddPatient] = useState(false);
  const [addPatientMode, setAddPatientMode] =
    useState<AddPatientMode>("manual");
  const [addingPatient, setAddingPatient] = useState(false);
  const [deletingSelected, setDeletingSelected] = useState(false);
  const [patientUploading, setPatientUploading] = useState(false);
  const patientFileRef = useRef<HTMLInputElement>(null);
  const [newPatient, setNewPatient] = useState({
    lab_number: "",
    im_lab_number: "",
    name: "",
    hkid: "",
    dob: "",
    sex: "",
    age: "",
    age_unit: "",
    ethnicity: "",
    specimen_collected: "",
    specimen_arrived: "",
    report_date: "",
    case_history: "",
    type_of_test: "",
    type_of_findings: "",
    findings_summary: "",
    ngs_batch: "",
    ngs_tat: "",
    ngs_tat_final: "",
    request_dr: "",
    remark: "",
  });

  const [extractMode, setExtractMode] = useState<ExtractMode>("all_files");
  const [extractFileTypes, setExtractFileTypes] = useState<Set<string>>(
    new Set(["singletons", "trios", "vcf_files"]),
  );
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Dropdown filter options
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    sex: [],
    type_of_test: [],
    terms: [],
  });
  const [selectedSex, setSelectedSex] = useState<Set<number>>(new Set());
  const [selectedTest, setSelectedTest] = useState<Set<number>>(new Set());
  const [selectedTerms, setSelectedTerms] = useState<Set<number>>(new Set());

  // Load filter options once
  useEffect(() => {
    fetchFilterOptions().then(setFilterOptions);
  }, []);

  // Build dropdown items from filterOptions
  const sexItems: DropdownItem[] = filterOptions.sex.map((s, i) => ({
    id: i,
    label: s,
  }));
  const testItems: DropdownItem[] = filterOptions.type_of_test.map((t, i) => ({
    id: i,
    label: t,
  }));
  const fetchTermItems = useCallback(
    async (search: string, limit: number, offset: number) => {
      const result = await fetchCombinedTermOptions(search, limit, offset);
      return {
        items: result.items.map((t) => ({
          id: t.id,
          label: t.label,
        })),
        total: result.total,
      };
    },
    [],
  );

  const loadPatients = useCallback(
    async (f: Filters, offset = 0, limit = PAGE_SIZE, append = false) => {
      const apiFilters: PatientListFilters = {};
      if (f.lab_number) apiFilters.lab_number = f.lab_number;
      if (f.im_lab_number) apiFilters.im_lab_number = f.im_lab_number;
      if (f.name) apiFilters.name = f.name;
      if (f.sex) apiFilters.sex = f.sex;
      if (f.age) apiFilters.age = f.age;
      if (f.type_of_test) apiFilters.type_of_test = f.type_of_test;
      if (f.term_ids) apiFilters.term_ids = f.term_ids;

      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      try {
        const data = await fetchPatientList(apiFilters, limit, offset);
        if (append) {
          setPatients((prev) => [...prev, ...data.items]);
        } else {
          setPatients(data.items);
        }
        setTotal(data.total);
      } catch {
        if (!append) setPatients([]);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [],
  );

  // Initial load
  useEffect(() => {
    loadPatients(emptyFilters);
  }, [loadPatients]);

  // Debounced filter changes
  const setFilter = (key: keyof Filters, value: string) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => loadPatients(next), 300);
  };

  const clearFilters = () => {
    setFilters(emptyFilters);
    setSelectedSex(new Set());
    setSelectedTest(new Set());
    setSelectedTerms(new Set());
    loadPatients(emptyFilters);
  };

  // Dropdown toggle helpers
  const toggleSex = (id: number) => {
    setSelectedSex((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      // Build comma-separated sex values for API
      const labels = [...next]
        .map((i) => sexItems.find((s) => s.id === i)?.label)
        .filter(Boolean)
        .join(",");
      const nextFilters = { ...filters, sex: labels };
      setFilters(nextFilters);
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => loadPatients(nextFilters), 300);
      return next;
    });
  };

  const toggleTest = (id: number) => {
    setSelectedTest((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      const labels = [...next]
        .map((i) => testItems.find((t) => t.id === i)?.label)
        .filter(Boolean)
        .join(",");
      const nextFilters = { ...filters, type_of_test: labels };
      setFilters(nextFilters);
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => loadPatients(nextFilters), 300);
      return next;
    });
  };

  const toggleTerm = (id: number) => {
    setSelectedTerms((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      const ids = [...next].join(",");
      const nextFilters = { ...filters, term_ids: ids };
      setFilters(nextFilters);
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => loadPatients(nextFilters), 300);
      return next;
    });
  };

  const remaining = total - patients.length;

  const handleLoadMore = () => {
    loadPatients(filters, patients.length, LOAD_MORE_SIZE, true);
  };

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleAll = () => {
    if (selected.size === patients.length && patients.length > 0) {
      setSelected(new Set());
    } else {
      setSelected(new Set(patients.map((p) => p.id)));
    }
  };

  const extract = async () => {
    setActionMsg(null);
    if (selected.size === 0) return;

    try {
      if (extractMode === "common_variants") {
        if (selected.size < 2) {
          setActionMsg({
            type: "error",
            msg: "Select at least 2 patients to find common variants.",
          });
          return;
        }
        await downloadCommonVariantsVcf([...selected]);
        setActionMsg({
          type: "success",
          msg: "Common-variants VCF downloaded.",
        });
        return;
      }

      if (extractMode === "selected_files" && extractFileTypes.size === 0) {
        setActionMsg({
          type: "error",
          msg: "Choose at least one file type for 'Selected files'.",
        });
        return;
      }

      const data = await extractSelectedPatients(
        [...selected],
        extractMode === "selected_files" ? "selected_files" : "all_files",
        [...extractFileTypes] as Array<"singletons" | "trios" | "vcf_files">,
      );
      setResults(data);
    } catch (e: unknown) {
      setActionMsg({
        type: "error",
        msg: e instanceof Error ? e.message : "Extraction failed",
      });
    }
  };

  const handleDeletePatient = async (patient: PatientInfo) => {
    if (!confirm(`Delete patient ${displayPatientId(patient)}?`)) return;
    setActionMsg(null);
    try {
      await deletePatient(patient.id);
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(patient.id);
        return next;
      });
      setResults((prev) =>
        prev ? prev.filter((row) => row.id !== patient.id) : prev,
      );
      await loadPatients(filters);
      setActionMsg({
        type: "success",
        msg: `Patient ${displayPatientId(patient)} deleted.`,
      });
    } catch (e: unknown) {
      setActionMsg({
        type: "error",
        msg: e instanceof Error ? e.message : "Failed to delete patient",
      });
    }
  };

  const handleDeleteSelected = async () => {
    const selectedIds = [...selected];
    if (selectedIds.length === 0) return;
    if (!confirm(`Delete ${selectedIds.length} selected patient(s)?`)) return;

    setDeletingSelected(true);
    setActionMsg(null);

    try {
      const failedIds = new Set<number>();
      const idToLab = new Map(patients.map((p) => [p.id, displayPatientId(p)]));

      for (const id of selectedIds) {
        try {
          await deletePatient(id);
        } catch {
          failedIds.add(id);
        }
      }

      const deletedCount = selectedIds.length - failedIds.size;
      const remainingSelected = new Set(
        selectedIds.filter((id) => failedIds.has(id)),
      );

      setSelected(remainingSelected);
      setResults((prev) =>
        prev ? prev.filter((row) => !selectedIds.includes(row.id)) : prev,
      );

      await loadPatients(filters);

      if (failedIds.size === 0) {
        setActionMsg({
          type: "success",
          msg: `Deleted ${deletedCount} selected patient(s).`,
        });
      } else {
        const failedLabs = [...failedIds]
          .map((id) => idToLab.get(id) ?? `#${id}`)
          .join(", ");
        setActionMsg({
          type: "error",
          msg: `Deleted ${deletedCount} patient(s). Failed to delete: ${failedLabs}`,
        });
      }
    } catch {
      setActionMsg({
        type: "error",
        msg: "Failed to delete selected patients.",
      });
    } finally {
      setDeletingSelected(false);
    }
  };

  const toggleExtractFileType = (
    name: "singletons" | "trios" | "vcf_files",
  ) => {
    setExtractFileTypes((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handlePatientListUpload = async () => {
    if (!patientFileRef.current?.files?.length) return;
    const file = patientFileRef.current.files[0];
    setPatientUploading(true);
    setActionMsg(null);
    try {
      const r = await uploadPatientsXlsx(file);
      setActionMsg({ type: "success", msg: r.message });
      if (patientFileRef.current) patientFileRef.current.value = "";
      await loadPatients(filters);
    } catch (e: unknown) {
      setActionMsg({
        type: "error",
        msg: e instanceof Error ? e.message : "Patient list upload failed",
      });
    } finally {
      setPatientUploading(false);
    }
  };

  const handleAddPatient = async () => {
    const lab = newPatient.lab_number.trim();
    if (!lab) {
      setActionMsg({ type: "error", msg: "Lab number is required" });
      return;
    }
    if (!isValidLabNumber(lab)) {
      setActionMsg({
        type: "error",
        msg: "Invalid lab number format. Use IM###... or 24AB###...",
      });
      return;
    }

    setAddingPatient(true);
    setActionMsg(null);
    try {
      const payload = {
        lab_number: lab,
        im_lab_number: trimOrUndefined(newPatient.im_lab_number),
        name: trimOrUndefined(newPatient.name),
        hkid: trimOrUndefined(newPatient.hkid),
        dob: trimOrUndefined(newPatient.dob),
        sex: trimOrUndefined(newPatient.sex),
        age: trimOrUndefined(newPatient.age),
        age_unit: trimOrUndefined(newPatient.age_unit),
        ethnicity: trimOrUndefined(newPatient.ethnicity),
        specimen_collected: trimOrUndefined(newPatient.specimen_collected),
        specimen_arrived: trimOrUndefined(newPatient.specimen_arrived),
        report_date: trimOrUndefined(newPatient.report_date),
        case_history: trimOrUndefined(newPatient.case_history),
        type_of_test: trimOrUndefined(newPatient.type_of_test),
        type_of_findings: trimOrUndefined(newPatient.type_of_findings),
        findings_summary: trimOrUndefined(newPatient.findings_summary),
        ngs_batch: trimOrUndefined(newPatient.ngs_batch),
        ngs_tat: trimOrUndefined(newPatient.ngs_tat),
        ngs_tat_final: trimOrUndefined(newPatient.ngs_tat_final),
        request_dr: trimOrUndefined(newPatient.request_dr),
        remark: trimOrUndefined(newPatient.remark),
      };
      await createPatient(payload);
      setActionMsg({
        type: "success",
        msg: `Patient ${lab} added successfully`,
      });
      setNewPatient({
        lab_number: "",
        im_lab_number: "",
        name: "",
        hkid: "",
        dob: "",
        sex: "",
        age: "",
        age_unit: "",
        ethnicity: "",
        specimen_collected: "",
        specimen_arrived: "",
        report_date: "",
        case_history: "",
        type_of_test: "",
        type_of_findings: "",
        findings_summary: "",
        ngs_batch: "",
        ngs_tat: "",
        ngs_tat_final: "",
        request_dr: "",
        remark: "",
      });
      await loadPatients(filters);
    } catch (e: unknown) {
      setActionMsg({
        type: "error",
        msg: e instanceof Error ? e.message : "Failed to add patient",
      });
    } finally {
      setAddingPatient(false);
    }
  };

  const baseUrl = `${window.location.protocol}//${window.location.host}`;
  const selectedIds = [...selected];

  return (
    <>
      <h2>Patients</h2>
      <p className="text-muted mb-2">
        Filter by any column, select patients, then click{" "}
        <strong>Extract Selected</strong> to get import instructions for your
        analysis tool.
      </p>

      <div className="flex-between mb-2">
        <button
          className="btn btn-primary"
          onClick={() => setShowAddPatient((s) => !s)}
        >
          {showAddPatient ? "Close Add Patient" : "Add Patient"}
        </button>
      </div>

      {showAddPatient && (
        <div className="card mb-2">
          <div className="card-header primary">Add Patient</div>
          <div className="card-body">
            <div className="flex-gap mb-1">
              <label style={{ cursor: "pointer" }}>
                <input
                  type="radio"
                  name="addPatientMode"
                  value="manual"
                  checked={addPatientMode === "manual"}
                  onChange={() => setAddPatientMode("manual")}
                />{" "}
                Manual input
              </label>
              <label style={{ cursor: "pointer" }}>
                <input
                  type="radio"
                  name="addPatientMode"
                  value="upload"
                  checked={addPatientMode === "upload"}
                  onChange={() => setAddPatientMode("upload")}
                />{" "}
                Upload file (.xlsx)
              </label>
            </div>

            {addPatientMode === "upload" ? (
              <div className="flex-gap">
                <input
                  ref={patientFileRef}
                  type="file"
                  className="form-control"
                  accept=".xlsx"
                  style={{ maxWidth: "420px" }}
                />
                <button
                  className="btn btn-primary"
                  disabled={patientUploading}
                  onClick={handlePatientListUpload}
                >
                  {patientUploading ? "Importing…" : "Import Patients"}
                </button>
              </div>
            ) : (
              <>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Lab Number *</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.lab_number}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          lab_number: e.target.value,
                        }))
                      }
                      placeholder="e.g. IM123 or 24AB001"
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>IM Lab Number</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.im_lab_number}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          im_lab_number: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Name</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.name}
                      onChange={(e) =>
                        setNewPatient((p) => ({ ...p, name: e.target.value }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>HKID</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.hkid}
                      onChange={(e) =>
                        setNewPatient((p) => ({ ...p, hkid: e.target.value }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>DOB</strong>
                    </label>
                    <input
                      type="date"
                      className="form-control"
                      value={newPatient.dob}
                      onChange={(e) =>
                        setNewPatient((p) => ({ ...p, dob: e.target.value }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Sex</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.sex}
                      onChange={(e) =>
                        setNewPatient((p) => ({ ...p, sex: e.target.value }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Age</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.age}
                      onChange={(e) =>
                        setNewPatient((p) => ({ ...p, age: e.target.value }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Age Unit</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.age_unit}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          age_unit: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Ethnicity</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.ethnicity}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          ethnicity: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Specimen Collected</strong>
                    </label>
                    <input
                      type="date"
                      className="form-control"
                      value={newPatient.specimen_collected}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          specimen_collected: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Specimen Arrived</strong>
                    </label>
                    <input
                      type="date"
                      className="form-control"
                      value={newPatient.specimen_arrived}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          specimen_arrived: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Report Date</strong>
                    </label>
                    <input
                      type="date"
                      className="form-control"
                      value={newPatient.report_date}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          report_date: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Type of Test</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.type_of_test}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          type_of_test: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Type of Findings</strong>
                    </label>
                    <select
                      className="form-control"
                      value={newPatient.type_of_findings}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          type_of_findings: e.target.value,
                        }))
                      }
                    >
                      <option value="">Select finding type…</option>
                      {FINDING_OPTIONS.filter((o) => o !== "").map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Case History</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.case_history}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          case_history: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Findings Summary</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.findings_summary}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          findings_summary: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>NGS Batch</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.ngs_batch}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          ngs_batch: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>NGS TAT</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.ngs_tat}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          ngs_tat: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>NGS TAT Final</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.ngs_tat_final}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          ngs_tat_final: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Requesting Doctor</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.request_dr}
                      onChange={(e) =>
                        setNewPatient((p) => ({
                          ...p,
                          request_dr: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="row mb-1">
                  <div className="col-2">
                    <label className="mb-1">
                      <strong>Remark</strong>
                    </label>
                    <input
                      className="form-control"
                      value={newPatient.remark}
                      onChange={(e) =>
                        setNewPatient((p) => ({ ...p, remark: e.target.value }))
                      }
                    />
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  disabled={addingPatient}
                  onClick={handleAddPatient}
                >
                  {addingPatient ? "Adding…" : "Create Patient"}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      <div className="card mb-2">
        <div className="card-header primary">Extraction Options</div>
        <div className="card-body">
          <div className="flex-gap" style={{ flexWrap: "wrap" }}>
            <label style={{ cursor: "pointer" }}>
              <input
                type="radio"
                name="extractMode"
                value="selected_files"
                checked={extractMode === "selected_files"}
                onChange={() => setExtractMode("selected_files")}
              />{" "}
              Selected files
            </label>
            <label style={{ cursor: "pointer" }}>
              <input
                type="radio"
                name="extractMode"
                value="all_files"
                checked={extractMode === "all_files"}
                onChange={() => setExtractMode("all_files")}
              />{" "}
              All files
            </label>
            <label style={{ cursor: "pointer" }}>
              <input
                type="radio"
                name="extractMode"
                value="common_variants"
                checked={extractMode === "common_variants"}
                onChange={() => setExtractMode("common_variants")}
              />{" "}
              Find common variants
            </label>
          </div>

          {extractMode === "selected_files" && (
            <div className="flex-gap mt-1" style={{ flexWrap: "wrap" }}>
              <label style={{ cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={extractFileTypes.has("singletons")}
                  onChange={() => toggleExtractFileType("singletons")}
                />{" "}
                Singleton variants
              </label>
              <label style={{ cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={extractFileTypes.has("trios")}
                  onChange={() => toggleExtractFileType("trios")}
                />{" "}
                Trio variants
              </label>
              <label style={{ cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={extractFileTypes.has("vcf_files")}
                  onChange={() => toggleExtractFileType("vcf_files")}
                />{" "}
                VCF files
              </label>
            </div>
          )}

          {extractMode === "common_variants" && (
            <p className="text-muted mt-1" style={{ marginBottom: 0 }}>
              Uses selected patients' VCF records and matches by CHROM, POS,
              REF, ALT. This option requires at least 2 selected patients.
            </p>
          )}
        </div>
      </div>

      {actionMsg && (
        <div
          className={`alert ${
            actionMsg.type === "success" ? "alert-success" : "alert-danger"
          }`}
        >
          {actionMsg.msg}
        </div>
      )}

      {/* ── Patient table with per-column filters ────────────────────── */}
      <div className="table-wrap table-scroll">
        <table>
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={
                    selected.size === patients.length && patients.length > 0
                  }
                  onChange={toggleAll}
                />
              </th>
              <th>Patient ID</th>
              <th>Lab Number</th>
              <th>Name</th>
              <th>Sex</th>
              <th>Age</th>
              <th>Test Type</th>
              <th className="disease-terms-col">Disease Terms</th>
              <th />
            </tr>
            <tr className="filter-row">
              <th />
              <th>
                <input
                  type="text"
                  placeholder="Filter…"
                  value={filters.im_lab_number}
                  onChange={(e) => setFilter("im_lab_number", e.target.value)}
                />
              </th>
              <th>
                <input
                  type="text"
                  placeholder="Filter…"
                  value={filters.lab_number}
                  onChange={(e) => setFilter("lab_number", e.target.value)}
                />
              </th>
              <th>
                <input
                  type="text"
                  placeholder="Filter…"
                  value={filters.name}
                  onChange={(e) => setFilter("name", e.target.value)}
                />
              </th>
              <th>
                <DropdownSelect
                  items={sexItems}
                  placeholder="All"
                  selectedIds={selectedSex}
                  onToggle={toggleSex}
                />
              </th>
              <th>
                <input
                  type="text"
                  placeholder="Filter…"
                  value={filters.age}
                  onChange={(e) => setFilter("age", e.target.value)}
                />
              </th>
              <th>
                <DropdownSelect
                  items={testItems}
                  placeholder="All"
                  selectedIds={selectedTest}
                  onToggle={toggleTest}
                />
              </th>
              <th className="disease-terms-col">
                <SearchableMultiSelect
                  selectedIds={selectedTerms}
                  onToggle={toggleTerm}
                  fetchOptions={fetchTermItems}
                  placeholder="Search disease terms…"
                  itemLabel="disease terms"
                  pageSize={20}
                  loadMoreSize={200}
                />
              </th>
              <th>
                <button
                  className="btn btn-outline-secondary btn-sm"
                  onClick={clearFilters}
                  title="Clear all filters"
                >
                  ✕
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} className="text-center text-muted">
                  Loading…
                </td>
              </tr>
            ) : patients.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center text-muted">
                  No patients match the current filters.
                </td>
              </tr>
            ) : (
              patients.map((p) => (
                <tr
                  key={p.id}
                  className={selected.has(p.id) ? "row-selected" : ""}
                >
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(p.id)}
                      onChange={() => toggle(p.id)}
                    />
                  </td>
                  <td>
                    <Link to={`/patients/${p.id}`}>
                      <code title={`Lab ${p.lab_number}`}>
                        {displayPatientId(p)}
                      </code>
                    </Link>
                  </td>
                  <td>{p.lab_number ?? "—"}</td>
                  <td>{p.name ?? "—"}</td>
                  <td>{p.sex ?? "—"}</td>
                  <td>
                    {p.age != null ? `${p.age} ${p.age_unit ?? ""}` : "—"}
                  </td>
                  <td>{p.type_of_test ?? "—"}</td>
                  <td className="disease-terms-col">
                    {(p.hpo_terms?.length ?? 0) +
                      (p.disease_terms?.length ?? 0) >
                    0
                      ? [
                          ...(p.hpo_terms ?? []).map((t) => ({
                            key: `hpo-${t.id}`,
                            label: t.hpo_id,
                            title: t.term_name,
                          })),
                          ...(p.disease_terms ?? []).map((t) => ({
                            key: `disease-${t.id}`,
                            label: t.term_name,
                            title: t.term_name,
                          })),
                        ].map((term) => (
                          <span
                            className="badge"
                            key={term.key}
                            title={term.title}
                          >
                            {term.label}
                          </span>
                        ))
                      : "—"}
                  </td>
                  <td>
                    <button
                      className="btn btn-outline-danger btn-sm"
                      onClick={() => handleDeletePatient(p)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex-between mt-2">
        <div className="flex-gap">
          <button
            className="btn btn-primary"
            disabled={selected.size === 0}
            onClick={extract}
          >
            Extract Selected ({selected.size})
          </button>
          <button
            className="btn btn-outline-danger"
            disabled={selected.size === 0 || deletingSelected}
            onClick={handleDeleteSelected}
          >
            {deletingSelected
              ? "Deleting…"
              : `Delete Selected (${selected.size})`}
          </button>
          {remaining > 0 && (
            <button
              className="btn btn-outline-secondary"
              disabled={loadingMore}
              onClick={handleLoadMore}
            >
              {loadingMore
                ? "Loading…"
                : `Load more patients (${remaining} remaining)`}
            </button>
          )}
        </div>
        <span className="text-muted">
          {patients.length} of {total} patient{total !== 1 ? "s" : ""} shown
        </span>
      </div>

      {/* ── Analysis tools panel (shown after extraction) ────────────── */}
      {results && (
        <>
          <hr />
          <h3>Import Selected Data</h3>
          <p className="text-muted mb-1">
            Use the snippets below to pull the {results.length} selected
            patient(s) into your analysis environment. If you're on a{" "}
            <strong>remote device</strong>, replace <code>localhost</code> with
            the server's IP address or hostname.
          </p>

          {/* Tabs */}
          <div className="tabs mb-1">
            {(Object.keys(TAB_LABELS) as ToolTab[]).map((tab) => (
              <button
                key={tab}
                className={`tab ${activeTab === tab ? "tab-active" : ""}`}
                onClick={() => setActiveTab(tab)}
              >
                {TAB_LABELS[tab]}
              </button>
            ))}
          </div>

          {/* Code block */}
          <div className="code-block">
            <div className="code-header">
              <span>{TAB_LABELS[activeTab]}</span>
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() =>
                  navigator.clipboard.writeText(
                    codeBlock(selectedIds, baseUrl, activeTab),
                  )
                }
              >
                Copy
              </button>
            </div>
            <pre>
              <code>{codeBlock(selectedIds, baseUrl, activeTab)}</code>
            </pre>
          </div>

          {/* Quick reference: selected patients summary */}
          <details className="mt-2">
            <summary>
              <strong>Selected patients summary</strong>
            </summary>
            <div className="table-wrap mt-1">
              <table>
                <thead>
                  <tr>
                    <th>Patient ID</th>
                    <th>Name</th>
                    <th>Test</th>
                    <th>Findings</th>
                    <th>Singletons</th>
                    <th>Trios</th>
                    <th>VCF Files</th>
                    <th>Disease Terms</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <Link to={`/patients/${p.id}`}>
                          <code title={`Lab ${p.lab_number}`}>
                            {displayPatientId(p)}
                          </code>
                        </Link>
                      </td>
                      <td>{p.name ?? "—"}</td>
                      <td>{p.type_of_test ?? "—"}</td>
                      <td>{p.type_of_findings ?? "—"}</td>
                      <td>{p.singletons?.length ?? 0}</td>
                      <td>{p.trios?.length ?? 0}</td>
                      <td>{p.vcf_files?.length ?? 0}</td>
                      <td>
                        {(p.hpo_terms?.length ?? 0) +
                          (p.disease_terms?.length ?? 0) >
                        0
                          ? [
                              ...(p.hpo_terms ?? []).map((t) => ({
                                key: `hpo-${t.id}`,
                                label: t.hpo_id,
                              })),
                              ...(p.disease_terms ?? []).map((t) => ({
                                key: `disease-${t.id}`,
                                label: t.term_name,
                              })),
                            ].map((term) => (
                              <span className="badge" key={term.key}>
                                {term.label}
                              </span>
                            ))
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </>
  );
}
