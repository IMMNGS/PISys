import { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import {
  fetchPatientList,
  fetchSelectedPatients,
  fetchFilterOptions,
} from "../api/client";
import type { PatientInfo } from "../types";
import type { PatientListFilters, FilterOptions } from "../api/client";
import DropdownSelect from "../components/DropdownSelect";
import type { DropdownItem } from "../components/DropdownSelect";

/* ── Tab definitions for the code-guide panel ─────────────────────────── */
type ToolTab = "python" | "r" | "curl" | "sql";

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

# Fetch HPO terms for a patient
curl ${baseUrl}/api/patients/${ids[0] ?? 1}/hpo_terms
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

-- Patients with HPO terms
SELECT p.lab_number, p.name, h.hpo_id, h.term_name
FROM patients p
JOIN patient_hpo ph ON ph.patient_id = p.id
JOIN hpo_terms h ON h.id = ph.hpo_term_id
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
  hpo_term_ids: string;
}

const emptyFilters: Filters = {
  lab_number: "",
  im_lab_number: "",
  name: "",
  sex: "",
  age: "",
  type_of_test: "",
  hpo_term_ids: "",
};

const PAGE_SIZE = 20;
const LOAD_MORE_SIZE = 100;

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
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Dropdown filter options
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    sex: [],
    type_of_test: [],
    hpo_terms: [],
  });
  const [selectedSex, setSelectedSex] = useState<Set<number>>(new Set());
  const [selectedTest, setSelectedTest] = useState<Set<number>>(new Set());
  const [selectedHpo, setSelectedHpo] = useState<Set<number>>(new Set());

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
  const hpoItems: DropdownItem[] = filterOptions.hpo_terms.map((h) => ({
    id: h.id,
    label: h.hpo_id,
    shortLabel: h.hpo_id,
  }));

  const loadPatients = useCallback(
    async (f: Filters, offset = 0, limit = PAGE_SIZE, append = false) => {
      const apiFilters: PatientListFilters = {};
      if (f.lab_number) apiFilters.lab_number = f.lab_number;
      if (f.im_lab_number) apiFilters.im_lab_number = f.im_lab_number;
      if (f.name) apiFilters.name = f.name;
      if (f.sex) apiFilters.sex = f.sex;
      if (f.age) apiFilters.age = f.age;
      if (f.type_of_test) apiFilters.type_of_test = f.type_of_test;
      if (f.hpo_term_ids) apiFilters.hpo_term_ids = f.hpo_term_ids;

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
    setSelectedHpo(new Set());
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

  const toggleHpo = (id: number) => {
    setSelectedHpo((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      const ids = [...next].join(",");
      const nextFilters = { ...filters, hpo_term_ids: ids };
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
    const data = await fetchSelectedPatients([...selected]);
    setResults(data);
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
              <th>Lab Number</th>
              <th>IM Lab Number</th>
              <th>Name</th>
              <th>Sex</th>
              <th>Age</th>
              <th>Test Type</th>
              <th>HPO Terms</th>
              <th />
            </tr>
            <tr className="filter-row">
              <th />
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
                  value={filters.im_lab_number}
                  onChange={(e) => setFilter("im_lab_number", e.target.value)}
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
              <th>
                <DropdownSelect
                  items={hpoItems}
                  placeholder="All"
                  selectedIds={selectedHpo}
                  onToggle={toggleHpo}
                  // Custom trigger label for HPO: only show IDs
                  pageSize={20}
                  {...{
                    triggerLabel: (items: DropdownItem[], selectedIds: Set<number>, placeholder: string) =>
                      selectedIds.size > 0
                        ? items.filter(i => selectedIds.has(i.id)).map(i => i.shortLabel ?? i.label).join(", ")
                        : placeholder
                  }}
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
                      <code>{p.lab_number}</code>
                    </Link>
                  </td>
                  <td>{p.im_lab_number ?? "—"}</td>
                  <td>{p.name ?? "—"}</td>
                  <td>{p.sex ?? "—"}</td>
                  <td>
                    {p.age != null ? `${p.age} ${p.age_unit ?? ""}` : "—"}
                  </td>
                  <td>{p.type_of_test ?? "—"}</td>
                  <td>
                    {p.hpo_terms && p.hpo_terms.length > 0
                      ? p.hpo_terms.map((t) => (
                          <span
                            className="badge"
                            key={t.id}
                            title={t.term_name}
                          >
                            {t.hpo_id}
                          </span>
                        ))
                      : "—"}
                  </td>
                  <td />
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
                    <th>Lab #</th>
                    <th>Name</th>
                    <th>Test</th>
                    <th>Findings</th>
                    <th>Singletons</th>
                    <th>Trios</th>
                    <th>VCF Files</th>
                    <th>HPO</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <Link to={`/patients/${p.id}`}>
                          <code>{p.lab_number}</code>
                        </Link>
                      </td>
                      <td>{p.name ?? "—"}</td>
                      <td>{p.type_of_test ?? "—"}</td>
                      <td>{p.type_of_findings ?? "—"}</td>
                      <td>{p.singletons?.length ?? 0}</td>
                      <td>{p.trios?.length ?? 0}</td>
                      <td>{p.vcf_files?.length ?? 0}</td>
                      <td>
                        {p.hpo_terms.length > 0
                          ? p.hpo_terms.map((t) => (
                              <span className="badge" key={t.id}>
                                {t.hpo_id}
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
