import { useEffect, useState, useCallback, useMemo } from "react";
import {
  fetchQcBatches,
  deleteQcBatch,
  fetchAllQcRecords,
  fetchQcStats,
} from "../api/client";
import type { NgsQcBatchInfo, QcRecordWithPatient, QcStats } from "../types";

const API_BASE = "/api";

function fmtBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtNum(n: number | null): string {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function fmtMetric(val: string | number | null | undefined): string {
  if (val == null || val === "") return "—";
  const num = Number(val);
  if (!isNaN(num)) {
    return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(val);
}

const PANEL_METRIC_ORDER = [
  "Panel_total_genes",
  "Panel_total_exons",
  "Panel_total_bases",
  "Mean_coverage",
  "Median_coverage",
  "Average_depth_of_coverage",
  "Total_aligned_reads",
  "Aligned_reads",
  "Aligned_reads(%)",
  "Duplicated_reads",
  "Duplicated_reads(%)",
  "Uniformity",
  "Uniformity(%)",
  "Coverage_20X",
  "Coverage_20X(%)",
  "Number_of_SNPs",
  "Number_of_indels",
  "Variant_number",
  "Heterozygous_to_Homozygous_ratio",
  "Ts_to_Tv_ratio",
];

const EXOME_METRIC_ORDER = [
  "# Reads",
  "% Reads",
  "% Perfect Index Reads",
  "qc_failed_reads_pct",
  "q30_bases_pct",
  "average_alignment_coverage_over_target_region",
  "median_autosomal_coverage_over_target_region",
  "number_of_duplicate_marked_reads_pct",
  "aligned_reads_in_target_region",
  "aligned_reads_in_target_region_pct",
  "uniformity_of_coverage_pct_gt_02mean_over_target_region",
  "pct_of_target_region_with_coverage_20x_inf",
  "variants_snps_pass",
  "variants_deletions_hom_pass",
  "variants_deletions_het_pass",
  "variants_insertions_hom_pass",
  "variants_insertions_het_pass",
  "variants_het_to_hom_ratio_pass",
  "variants_ti_to_tv_ratio_pass",
  "pct_reads_PF",
  "indel",
  "variant_number",
  "avg_cov_on_targ_30x_flag.",
];

type TabKey = "overview" | "batches" | "records";
type QcTypeFilter = "" | "panel" | "exome";
type PassFailFilter = "" | "PASS" | "FAIL" | "BORDERLINE";

export default function QcOverview() {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  // Filters
  const [batchFilter, setBatchFilter] = useState("");
  const [qcType, setQcType] = useState<QcTypeFilter>("");
  const [passFail, setPassFail] = useState<PassFailFilter>("");

  // Data
  const [batches, setBatches] = useState<NgsQcBatchInfo[]>([]);
  const [records, setRecords] = useState<QcRecordWithPatient[]>([]);
  const [stats, setStats] = useState<QcStats | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [b, r, s] = await Promise.all([
        fetchQcBatches(),
        fetchAllQcRecords({
          batch: batchFilter || undefined,
          qc_type: qcType || undefined,
          pass_fail: passFail || undefined,
        }),
        fetchQcStats({
          batch: batchFilter || undefined,
          qc_type: qcType || undefined,
        }),
      ]);
      setBatches(b);
      setRecords(r);
      setStats(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load QC data");
    } finally {
      setLoading(false);
    }
  }, [batchFilter, qcType, passFail]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDeleteBatch = async (batch: NgsQcBatchInfo) => {
    if (
      !confirm(
        `Delete QC batch "${batch.original_filename}"?\nThis will also remove all linked per-patient QC records.`,
      )
    )
      return;
    try {
      await deleteQcBatch(batch.id);
      setBatches((prev) => prev.filter((b) => b.id !== batch.id));
      load();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const clearFilters = () => {
    setBatchFilter("");
    setQcType("");
    setPassFail("");
  };

  const passFailColor = (pf: string | null) => {
    if (pf === "PASS") return "var(--success)";
    if (pf === "FAIL") return "var(--danger)";
    if (pf === "BORDERLINE") return "var(--warning)";
    return "var(--muted)";
  };

  const hasFilters = batchFilter || qcType || passFail;

  return (
    <>
      <div className="flex-between mb-2">
        <h2>QC Dashboard</h2>
        <span className="text-muted">
          {stats?.pass_fail.total ?? 0} patient record
          {stats?.pass_fail.total !== 1 ? "s" : ""} · {batches.length} batch
          {batches.length !== 1 ? "es" : ""}
        </span>
      </div>

      {/* ── Filters ─────────────────────────────────────────────── */}
      <div className="card mb-2">
        <div className="card-body" style={{ padding: "0.75rem 1rem" }}>
          <div
            className="row"
            style={{ alignItems: "flex-end", gap: "0.5rem", flexWrap: "wrap" }}
          >
            <div style={{ minWidth: "140px" }}>
              <label className="form-label" style={{ fontSize: "0.75rem" }}>
                Batch
              </label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. 26P1"
                value={batchFilter}
                onChange={(e) => setBatchFilter(e.target.value)}
              />
            </div>
            <div style={{ minWidth: "120px" }}>
              <label className="form-label" style={{ fontSize: "0.75rem" }}>
                Type
              </label>
              <select
                className="form-control"
                value={qcType}
                onChange={(e) => setQcType(e.target.value as QcTypeFilter)}
              >
                <option value="">All</option>
                <option value="panel">Panel</option>
                <option value="exome">Exome</option>
              </select>
            </div>
            <div style={{ minWidth: "140px" }}>
              <label className="form-label" style={{ fontSize: "0.75rem" }}>
                Pass / Fail
              </label>
              <select
                className="form-control"
                value={passFail}
                onChange={(e) => setPassFail(e.target.value as PassFailFilter)}
              >
                <option value="">All</option>
                <option value="PASS">PASS</option>
                <option value="FAIL">FAIL</option>
                <option value="BORDERLINE">BORDERLINE</option>
              </select>
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={clearFilters}
                disabled={!hasFilters}
              >
                Clear
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => {
                  const params = new URLSearchParams();
                  if (batchFilter) params.set("batch", batchFilter);
                  if (qcType) params.set("qc_type", qcType);
                  if (passFail) params.set("pass_fail", passFail);
                  const qs = params.toString();
                  const url = `${API_BASE}/qc/records/download${qs ? "?" + qs : ""}`;
                  window.location.href = url;
                }}
              >
                Download Excel
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {/* ── Tabs ────────────────────────────────────────────────── */}
      <div className="tabs" style={{ marginBottom: "0.75rem" }}>
        {([
          { key: "overview", label: "Overview & Stats" },
          { key: "batches", label: "Batches" },
          { key: "records", label: "QC Records" }
        ] as { key: TabKey; label: string }[]).map((t) => (
          <button
            key={t.key}
            className={`tab${activeTab === t.key ? " tab-active" : ""}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-muted">Loading QC data…</p>
      ) : (
        <>
          {/* ── Overview & Stats tab ───────────────────────────── */}
          {activeTab === "overview" && (
            <>
              {/* Stat cards */}
              <div
                className="row mb-2"
                style={{ gap: "0.75rem", flexWrap: "wrap" }}
              >
                <StatCard
                  label="Avg Median Coverage"
                  value={fmtNum(stats?.averages.median_coverage ?? null)}
                  unit="x"
                />
                <StatCard
                  label="Avg % Target ≥20X"
                  value={fmtNum(stats?.averages.pct_20x ?? null)}
                  unit="%"
                />
                <StatCard
                  label="Avg Uniformity"
                  value={fmtNum(stats?.averages.uniformity_pct ?? null)}
                  unit="%"
                />
                <div className="card" style={{ flex: 1, minWidth: "200px" }}>
                  <div className="card-body">
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--muted)",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      Pass / Fail Distribution
                    </div>
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "0.5rem 1rem",
                        marginTop: "0.5rem",
                      }}
                    >
                      <span style={{ color: "var(--success)", fontWeight: 700 }}>
                        PASS: {stats?.pass_fail.pass ?? 0}
                      </span>
                      <span style={{ color: "var(--danger)", fontWeight: 700 }}>
                        FAIL: {stats?.pass_fail.fail ?? 0}
                      </span>
                      <span style={{ color: "var(--warning)", fontWeight: 700 }}>
                        BORDERLINE: {stats?.pass_fail.borderline ?? 0}
                      </span>
                      <span className="text-muted">
                        Total: {stats?.pass_fail.total ?? 0}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Batch summary table */}
              <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>
                Batch Trends (last 20)
              </h3>
              {stats && stats.batch_summaries.length > 0 ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Batch</th>
                        <th>Type</th>
                        <th>Avg Median Cov</th>
                        <th>Avg % ≥20X</th>
                        <th>Avg Uniformity</th>
                        <th>Records</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.batch_summaries.map((row) => (
                        <tr key={`${row.batch}-${row.qc_type}`}>
                          <td>
                            <code>{row.batch}</code>
                          </td>
                          <td>
                            <span
                              style={{
                                fontSize: "0.72rem",
                                fontWeight: 700,
                                padding: "0.1em 0.4em",
                                borderRadius: "0.2rem",
                                background:
                                  row.qc_type === "exome"
                                    ? "#ede9fe"
                                    : "#dbeafe",
                                color:
                                  row.qc_type === "exome"
                                    ? "#6d28d9"
                                    : "#1d4ed8",
                                textTransform: "uppercase",
                              }}
                            >
                              {row.qc_type}
                            </span>
                          </td>
                          <td>{fmtNum(row.avg_median_coverage)}x</td>
                          <td>{fmtNum(row.avg_pct_20x)}%</td>
                          <td>{fmtNum(row.avg_uniformity_pct)}%</td>
                          <td>{row.record_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-muted">No batch data available.</p>
              )}
            </>
          )}

          {/* ── Batches tab ──────────────────────────────────────── */}
          {activeTab === "batches" && (
            <>
              {batches.length === 0 ? (
                <p className="text-muted">No QC uploads yet.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Batch</th>
                        <th>Filename</th>
                        <th>Positive Control</th>
                        <th>Matched</th>
                        <th>Unmatched</th>
                        <th>Size</th>
                        <th>Uploaded</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {batches.map((b) => (
                        <tr key={b.id}>
                          <td>
                            <span
                              style={{
                                fontSize: "0.78rem",
                                fontWeight: 700,
                                padding: "0.15em 0.55em",
                                borderRadius: "0.25rem",
                                background:
                                  b.qc_type === "exome"
                                    ? "#ede9fe"
                                    : "#dbeafe",
                                color:
                                  b.qc_type === "exome"
                                    ? "#6d28d9"
                                    : "#1d4ed8",
                                textTransform: "uppercase",
                              }}
                            >
                              {b.qc_type}
                            </span>
                          </td>
                          <td>
                            {b.batch ? (
                              <code>{b.batch}</code>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td>
                            <code style={{ fontSize: "0.82rem" }}>
                              {b.original_filename ?? "—"}
                            </code>
                          </td>
                          <td>{b.positive_control_label ?? "—"}</td>
                          <td>{b.matched_count}</td>
                          <td>
                            {b.unmatched_labels.length > 0 ? (
                              <span className="text-danger">
                                {b.unmatched_labels.join(", ")}
                              </span>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td>{fmtBytes(b.file_size)}</td>
                          <td>{b.uploaded_at?.slice(0, 10) ?? "—"}</td>
                          <td>
                            <button
                              className="btn btn-outline-danger btn-sm"
                              onClick={() => handleDeleteBatch(b)}
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          {/* ── Per-Patient Records tab ──────────────────────────── */}
          {activeTab === "records" && (
            <>
              {records.length === 0 ? (
                <p className="text-muted">
                  No QC records match the current filters.
                </p>
              ) : (
                <RecordMetricsTable
                  records={records}
                  passFailColor={passFailColor}
                />
              )}
            </>
          )}
        </>
      )}
    </>
  );
}

function StatCard({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit?: string;
}) {
  return (
    <div className="card" style={{ flex: 1, minWidth: "160px" }}>
      <div className="card-body">
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--muted)",
            fontWeight: 600,
            textTransform: "uppercase",
          }}
        >
          {label}
        </div>
        <div style={{ fontSize: "1.4rem", fontWeight: 700, marginTop: "0.25rem" }}>
          {value}
          {unit && (
            <span style={{ fontSize: "0.9rem", color: "var(--muted)" }}>{unit}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function RecordMetricsTable({
  records,
  passFailColor,
}: {
  records: QcRecordWithPatient[];
  passFailColor: (pf: string | null) => string;
}) {
  const metricColumns = useMemo(() => {
    const hasPanel = records.some((r) => r.qc_type === "panel");
    const hasExome = records.some((r) => r.qc_type === "exome");

    const cols: string[] = [];
    if (hasPanel) cols.push(...PANEL_METRIC_ORDER);
    if (hasExome) cols.push(...EXOME_METRIC_ORDER);

    // Deduplicate while preserving order
    const seen = new Set<string>();
    const ordered: string[] = [];
    for (const c of cols) {
      if (!seen.has(c)) {
        seen.add(c);
        ordered.push(c);
      }
    }

    // Also include any extra keys found in records that aren't in the known lists
    for (const r of records) {
      for (const key of Object.keys(r.metrics || {})) {
        if (!seen.has(key)) {
          seen.add(key);
          ordered.push(key);
        }
      }
    }
    return ordered;
  }, [records]);

  const hasMetrics = metricColumns.length > 0;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th style={{ position: "sticky", left: 0, zIndex: 2, background: "var(--card-bg)" }}>
              Sample
            </th>
            <th>Batch</th>
            <th>Type</th>
            <th>Pass/Fail</th>
            {hasMetrics && (
              <th
                colSpan={metricColumns.length}
                style={{
                  textAlign: "center",
                  background: "#f1f5f9",
                  color: "#334155",
                  fontSize: "0.75rem",
                  letterSpacing: "0.05em",
                }}
              >
                Raw Metrics
              </th>
            )}
            <th>Uploaded</th>
          </tr>
          <tr>
            <th style={{ position: "sticky", left: 0, zIndex: 2, background: "var(--card-bg)" }} />
            <th />
            <th />
            <th />
            {metricColumns.map((key) => (
              <th
                key={key}
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: "var(--muted)",
                  minWidth: "100px",
                }}
                title={key}
              >
                {key}
              </th>
            ))}
            <th />
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.id}>
              <td
                style={{
                  position: "sticky",
                  left: 0,
                  zIndex: 1,
                  background: "var(--card-bg)",
                }}
              >
                <div>
                  {r.is_control ? (
                    <>
                      <code>{r.sample_label ?? "—"}</code>
                      <span
                        style={{
                          fontSize: "0.72rem",
                          fontWeight: 700,
                          padding: "0.1em 0.4em",
                          borderRadius: "0.2rem",
                          background: "#fef3c7",
                          color: "#92400e",
                          marginLeft: "0.4rem",
                          textTransform: "uppercase",
                        }}
                      >
                        Control
                      </span>
                    </>
                  ) : (
                    <>
                      <code>
                        {r.patient_im_lab_number ?? r.patient_lab_number ?? "—"}
                      </code>
                      {r.patient_name && (
                        <div className="text-muted" style={{ fontSize: "0.8rem" }}>
                          {r.patient_name}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </td>
              <td>
                {r.batch ? <code>{r.batch}</code> : <span className="text-muted">—</span>}
              </td>
              <td>
                <span
                  style={{
                    fontSize: "0.72rem",
                    fontWeight: 700,
                    padding: "0.1em 0.4em",
                    borderRadius: "0.2rem",
                    background: r.qc_type === "exome" ? "#ede9fe" : "#dbeafe",
                    color: r.qc_type === "exome" ? "#6d28d9" : "#1d4ed8",
                    textTransform: "uppercase",
                  }}
                >
                  {r.qc_type}
                </span>
              </td>
              <td>
                {r.pass_fail ? (
                  <span style={{ fontWeight: 700, color: passFailColor(r.pass_fail) }}>
                    {r.pass_fail}
                  </span>
                ) : (
                  <span className="text-muted">—</span>
                )}
              </td>
              {metricColumns.map((key) => (
                <td key={key} className="text-muted">
                  {fmtMetric(r.metrics?.[key])}
                </td>
              ))}
              <td>{r.uploaded_at?.slice(0, 10) ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
