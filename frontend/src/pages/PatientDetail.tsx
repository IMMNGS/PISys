import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import {
  fetchPatient,
  removeHPO,
  updatePatient,
  updateSingleton,
  updateTrio,
  fetchQcRecords,
  createQcRecord,
  uploadQcFile,
  deleteQcRecord,
  fetchVariantAudit,
  removePatientDiseaseTerm,
  fetchPatientDiseaseTerms,
} from "../api/client";
import type {
  PatientInfo,
  SingletonInfo,
  TrioInfo,
  NgsQcInfo,
  QcType,
  VariantAuditEntry,
  DiseaseTerm,
  VariantUploadInfo,
} from "../types";

type Tab = "overview" | "variants" | "qc" | "files" | "terms";
type VariantRow = (SingletonInfo | TrioInfo) & { _type: "singleton" | "trio" };

const PASS_FAIL_COLORS: Record<string, string> = {
  PASS: "var(--success)",
  FAIL: "var(--danger)",
  BORDERLINE: "var(--warning)",
};

function fmt(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  return String(v);
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toFixed(1)}%`;
}

function fmtNum(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toLocaleString();
}

function classificationBadge(cls: string | null) {
  const color =
    cls === "C"
      ? "#dc2626"
      : cls === "I"
        ? "#d97706"
        : cls === "A"
          ? "#2563eb"
          : "var(--muted)";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.1em 0.45em",
        borderRadius: "0.25rem",
        background: color,
        color: "#fff",
        fontSize: "0.78rem",
        fontWeight: 700,
      }}
    >
      {cls ?? "—"}
    </span>
  );
}

// ── Overview tab ─────────────────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <th style={{ whiteSpace: "nowrap", color: "var(--muted)", fontWeight: 600, width: "40%" }}>{label}</th>
      <td>{value || "—"}</td>
    </tr>
  );
}

function OverviewTab({
  patient,
  editing,
  form,
  saving,
  saveError,
  onStartEdit,
  onFieldChange,
  onSave,
  onCancelEdit,
}: {
  patient: PatientInfo;
  editing: boolean;
  form: Record<string, string>;
  saving: boolean;
  saveError: string | null;
  onStartEdit: () => void;
  onFieldChange: (k: string, v: string) => void;
  onSave: () => void;
  onCancelEdit: () => void;
}) {
  if (editing) {
    return (
      <div style={{ marginTop: "0.75rem" }}>
        {saveError && <div className="alert alert-danger mb-1">{saveError}</div>}
        <div className="card" style={{ padding: "1rem" }}>
          <div className="flex-between mb-1">
            <h3 style={{ margin: 0 }}>Edit Patient</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-success btn-sm" onClick={onSave} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
              <button className="btn btn-outline-secondary btn-sm" onClick={onCancelEdit} disabled={saving}>
                Cancel
              </button>
            </div>
          </div>
          <div className="row" style={{ gap: "0.75rem" }}>
            {[
              { key: "name", label: "Name" },
              { key: "hkid", label: "HKID" },
              { key: "im_lab_number", label: "IM Lab Number" },
              { key: "sex", label: "Sex" },
              { key: "age", label: "Age" },
              { key: "age_unit", label: "Age Unit" },
              { key: "ethnicity", label: "Ethnicity" },
              { key: "type_of_test", label: "Type of Test" },
              { key: "type_of_findings", label: "Type of Findings" },
              { key: "request_dr", label: "Request Dr" },
              { key: "ngs_batch", label: "NGS Batch" },
              { key: "ngs_tat", label: "NGS TAT" },
              { key: "ngs_tat_final", label: "NGS TAT Final" },
            ].map(({ key, label }) => (
              <div key={key} style={{ flex: "1 1 200px" }}>
                <label className="form-label">{label}</label>
                <input
                  className="form-control"
                  value={form[key] ?? ""}
                  onChange={(e) => onFieldChange(key, e.target.value)}
                />
              </div>
            ))}
            {[
              { key: "dob", label: "Date of Birth" },
              { key: "report_date", label: "Report Date" },
              { key: "specimen_collected", label: "Specimen Collected" },
              { key: "specimen_arrived", label: "Specimen Arrived" },
            ].map(({ key, label }) => (
              <div key={key} style={{ flex: "1 1 180px" }}>
                <label className="form-label">{label}</label>
                <input
                  type="date"
                  className="form-control"
                  value={form[key] ?? ""}
                  onChange={(e) => onFieldChange(key, e.target.value)}
                />
              </div>
            ))}
            {[
              { key: "clinical_history", label: "Clinical History", rows: 3 },
              { key: "findings_summary", label: "Findings Summary", rows: 2 },
              { key: "remark", label: "Remark", rows: 2 },
            ].map(({ key, label, rows }) => (
              <div key={key} style={{ flex: "1 1 100%" }}>
                <label className="form-label">{label}</label>
                <textarea
                  className="form-control"
                  rows={rows}
                  value={form[key] ?? ""}
                  onChange={(e) => onFieldChange(key, e.target.value)}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ marginTop: "0.75rem" }}>
      <div className="row">
        <div className="col-2">
          <div className="card" style={{ padding: "0.75rem 1rem" }}>
            <div className="flex-between mb-1">
              <strong>Demographics</strong>
              <button className="btn btn-outline btn-sm" onClick={onStartEdit}>
                Edit
              </button>
            </div>
            <div className="table-wrap">
              <table>
                <tbody>
                  <InfoRow label="Name" value={patient.name} />
                  <InfoRow label="HKID" value={patient.hkid} />
                  <InfoRow label="Date of Birth" value={patient.dob} />
                  <InfoRow label="Sex" value={patient.sex} />
                  <InfoRow
                    label="Age"
                    value={
                      patient.age != null
                        ? `${patient.age} ${patient.age_unit ?? ""}`.trim()
                        : null
                    }
                  />
                  <InfoRow label="Ethnicity" value={patient.ethnicity} />
                  <InfoRow label="IM Lab Number" value={patient.im_lab_number} />
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="col-2">
          <div className="card" style={{ padding: "0.75rem 1rem" }}>
            <strong className="mb-1" style={{ display: "block" }}>Clinical</strong>
            <div className="table-wrap">
              <table>
                <tbody>
                  <InfoRow
                    label="Clinical History"
                    value={
                      <span style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                        {patient.clinical_history ?? patient.case_history}
                      </span>
                    }
                  />
                  <InfoRow label="Type of Test" value={patient.type_of_test} />
                  <InfoRow label="Type of Findings" value={patient.type_of_findings} />
                  <InfoRow
                    label="Findings Summary"
                    value={
                      <span style={{ whiteSpace: "pre-wrap" }}>{patient.findings_summary}</span>
                    }
                  />
                  <InfoRow label="Request Dr" value={patient.request_dr} />
                  <InfoRow
                    label="Remark"
                    value={<span style={{ whiteSpace: "pre-wrap" }}>{patient.remark}</span>}
                  />
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "1rem", padding: "0.75rem 1rem" }}>
        <strong className="mb-1" style={{ display: "block" }}>NGS / Report</strong>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem" }}>
          {[
            ["Report Date", patient.report_date],
            ["Specimen Collected", patient.specimen_collected],
            ["Specimen Arrived", patient.specimen_arrived],
            ["NGS Batch", patient.ngs_batch],
            ["NGS TAT", patient.ngs_tat],
            ["NGS TAT Final", patient.ngs_tat_final],
            ["Created", patient.created_at?.slice(0, 10)],
          ].map(([label, value]) => (
            <div key={label as string}>
              <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600 }}>
                {label}
              </div>
              <div style={{ fontSize: "0.95rem" }}>{value || "—"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Variants tab ──────────────────────────────────────────────────────────

const VARIANT_EDIT_FIELDS: Array<{ key: string; label: string; type?: string }> = [
  { key: "gene_names", label: "Gene(s)" },
  { key: "classification", label: "Classification" },
  { key: "reportable_variant", label: "Reportable Variant" },
  { key: "chr_pos", label: "Chr:Pos" },
  { key: "ref_alt", label: "Ref/Alt" },
  { key: "hgvs_c", label: "HGVS c." },
  { key: "hgvs_p", label: "HGVS p." },
  { key: "exon_number", label: "Exon" },
  { key: "zygosity", label: "Zygosity" },
  { key: "inheritance", label: "Inheritance" },
  { key: "inherited_from", label: "Inherited From" },
  { key: "omim_id", label: "OMIM ID" },
  { key: "rsid", label: "RSID" },
  { key: "title", label: "Title" },
  { key: "second_review_comment", label: "2nd Review Comment" },
];

function VariantsTab({
  variants,
  onVariantUpdated,
}: {
  variants: VariantRow[];
  onVariantUpdated: (v: VariantRow) => void;
}) {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [editingVariant, setEditingVariant] = useState(false);
  const [variantForm, setVariantForm] = useState<Record<string, string>>({});
  const [variantSaving, setVariantSaving] = useState(false);
  const [variantError, setVariantError] = useState<string | null>(null);

  const selected = selectedIdx !== null ? variants[selectedIdx] : null;

  const openDetail = (idx: number) => {
    if (selectedIdx === idx) {
      setSelectedIdx(null);
      setEditingVariant(false);
    } else {
      setSelectedIdx(idx);
      setEditingVariant(false);
      setVariantError(null);
    }
  };

  const startEditVariant = () => {
    if (!selected) return;
    const f: Record<string, string> = {};
    const sel = selected as unknown as Record<string, unknown>;
    for (const { key } of VARIANT_EDIT_FIELDS) {
      f[key] = sel[key] != null ? String(sel[key]) : "";
    }
    f.igv_review = selected.igv_review ? "true" : "false";
    setVariantForm(f);
    setEditingVariant(true);
    setVariantError(null);
  };

  const saveVariant = async () => {
    if (!selected) return;
    setVariantSaving(true);
    setVariantError(null);
    try {
      const payload: Record<string, unknown> = {};
      for (const { key } of VARIANT_EDIT_FIELDS) {
        payload[key] = variantForm[key] || null;
      }
      payload.igv_review = variantForm.igv_review === "true";

      let updated: SingletonInfo | TrioInfo;
      if (selected._type === "singleton") {
        updated = await updateSingleton(selected.id, payload);
      } else {
        updated = await updateTrio(selected.id, payload);
      }
      onVariantUpdated({ ...updated, _type: selected._type });
      setEditingVariant(false);
    } catch (e) {
      setVariantError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setVariantSaving(false);
    }
  };

  if (variants.length === 0) {
    return <p className="text-muted" style={{ marginTop: "1rem" }}>No variant findings recorded.</p>;
  }

  return (
    <div style={{ marginTop: "0.75rem" }}>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Gene</th>
              <th>Classification</th>
              <th>Chr:Pos</th>
              <th>Ref/Alt</th>
              <th>Zygosity</th>
              <th>IGV</th>
              <th>Reportable</th>
            </tr>
          </thead>
          <tbody>
            {variants.map((v, idx) => (
              <tr
                key={`${v._type}-${v.id}`}
                className={selectedIdx === idx ? "row-selected" : ""}
                style={{ cursor: "pointer" }}
                onClick={() => openDetail(idx)}
              >
                <td>
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      padding: "0.1em 0.4em",
                      borderRadius: "0.25rem",
                      background: v._type === "singleton" ? "#dbeafe" : "#ede9fe",
                      color: v._type === "singleton" ? "#1d4ed8" : "#6d28d9",
                    }}
                  >
                    {v._type}
                  </span>
                </td>
                <td style={{ fontWeight: 600 }}>{v.gene_names ?? "—"}</td>
                <td>{classificationBadge(v.classification)}</td>
                <td>{v.chr_pos ?? "—"}</td>
                <td>{v.ref_alt ?? "—"}</td>
                <td>{v.zygosity ?? "—"}</td>
                <td>
                  <span style={{ color: v.igv_review ? "var(--success)" : "var(--muted)" }}>
                    {v.igv_review ? "✓" : "—"}
                  </span>
                </td>
                <td>{v.reportable_variant ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div
          className="card"
          style={{ marginTop: "0.75rem", padding: "1rem", border: "2px solid var(--primary)" }}
        >
          <div className="flex-between mb-1">
            <strong style={{ fontSize: "1rem" }}>
              {selected._type.charAt(0).toUpperCase() + selected._type.slice(1)} #{selected.id} —{" "}
              {selected.gene_names ?? "Unknown gene"}
            </strong>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {!editingVariant && (
                <button className="btn btn-outline btn-sm" onClick={startEditVariant}>
                  Edit
                </button>
              )}
              {editingVariant && (
                <>
                  <button
                    className="btn btn-success btn-sm"
                    onClick={saveVariant}
                    disabled={variantSaving}
                  >
                    {variantSaving ? "Saving…" : "Save"}
                  </button>
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setEditingVariant(false)}
                    disabled={variantSaving}
                  >
                    Cancel
                  </button>
                </>
              )}
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => setSelectedIdx(null)}
              >
                ✕
              </button>
            </div>
          </div>

          {variantError && <div className="alert alert-danger mb-1">{variantError}</div>}

          {editingVariant ? (
            <div className="row" style={{ gap: "0.75rem" }}>
              <div style={{ flex: "1 1 200px" }}>
                <label className="form-label">IGV Review</label>
                <select
                  className="form-control"
                  value={variantForm.igv_review}
                  onChange={(e) =>
                    setVariantForm((f) => ({ ...f, igv_review: e.target.value }))
                  }
                >
                  <option value="false">No</option>
                  <option value="true">Yes</option>
                </select>
              </div>
              {VARIANT_EDIT_FIELDS.map(({ key, label }) => (
                <div key={key} style={{ flex: "1 1 200px" }}>
                  <label className="form-label">{label}</label>
                  {key === "second_review_comment" ? (
                    <textarea
                      className="form-control"
                      rows={2}
                      value={variantForm[key] ?? ""}
                      onChange={(e) =>
                        setVariantForm((f) => ({ ...f, [key]: e.target.value }))
                      }
                    />
                  ) : (
                    <input
                      className="form-control"
                      value={variantForm[key] ?? ""}
                      onChange={(e) =>
                        setVariantForm((f) => ({ ...f, [key]: e.target.value }))
                      }
                    />
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "0.6rem" }}>
              {[
                ["IGV Review", selected.igv_review ? "Yes ✓" : "No"],
                ["2nd Review", selected.second_review_comment],
                ["Reportable", selected.reportable_variant],
                ["Classification", selected.classification],
                ["Gene(s)", selected.gene_names],
                ["Chr:Pos", selected.chr_pos],
                ["Ref/Alt", selected.ref_alt],
                ["HGVS c.", selected.hgvs_c],
                ["HGVS p.", selected.hgvs_p],
                ["Exon", selected.exon_number],
                ["Zygosity", selected.zygosity],
                ["Inheritance", selected.inheritance],
                ["Inherited From", selected.inherited_from],
                ["OMIM ID", selected.omim_id],
                ["RSID", selected.rsid],
                ["Title", selected.title],
                ["Gene Region", selected.gene_region_combined],
                ["Created", selected.created_at?.slice(0, 10)],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", fontWeight: 600 }}>
                    {label}
                  </div>
                  <div style={{ fontSize: "0.9rem", wordBreak: "break-word" }}>
                    {value || "—"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── QC tab ────────────────────────────────────────────────────────────────

function QcRecordCard({
  record,
  onDelete,
}: {
  record: NgsQcInfo;
  onDelete: (id: number) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const rawEntries = Object.entries(record.metrics ?? {});

  return (
    <div
      className="card"
      style={{ padding: "0.75rem 1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}
    >
      <div className="flex-between">
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
          <span
            style={{
              fontSize: "0.78rem",
              fontWeight: 700,
              padding: "0.15em 0.55em",
              borderRadius: "0.25rem",
              background: record.qc_type === "exome" ? "#ede9fe" : "#dbeafe",
              color: record.qc_type === "exome" ? "#6d28d9" : "#1d4ed8",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            {record.qc_type}
          </span>
          {record.pass_fail && (
            <span
              style={{
                fontWeight: 700,
                fontSize: "0.85rem",
                padding: "0.2em 0.6em",
                borderRadius: "0.35rem",
                background: PASS_FAIL_COLORS[record.pass_fail] ?? "var(--muted)",
                color: "#fff",
              }}
            >
              {record.pass_fail}
            </span>
          )}
          <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
            {record.uploaded_at?.slice(0, 10) ?? ""}
          </span>
          {record.batch && (
            <span
              style={{
                fontSize: "0.78rem",
                fontWeight: 600,
                padding: "0.15em 0.55em",
                borderRadius: "0.25rem",
                background: "#f3f4f6",
                color: "#374151",
              }}
            >
              {record.batch}
            </span>
          )}
          {record.original_filename && (
            <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
              · <code>{record.original_filename}</code>
            </span>
          )}
        </div>
        <button className="btn btn-outline-danger btn-sm" onClick={() => onDelete(record.id)}>
          Delete
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "0.6rem",
          background: "rgba(79, 70, 229, 0.04)",
          padding: "0.5rem 0.75rem",
          borderRadius: "0.4rem",
          border: "1px dashed rgba(79, 70, 229, 0.25)",
        }}
      >
        {[
          ["% of target ≥20X", fmtPct(record.pct_20x)],
          ["Uniformity (%)", fmtPct(record.uniformity_pct)],
          ["Median Coverage", record.median_coverage != null ? `${record.median_coverage.toFixed(1)}x` : "—"],
        ].map(([label, value]) => (
          <div key={label as string}>
            <div style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.03em" }}>
              {label} <span style={{ color: "var(--primary)" }}>↳ report</span>
            </div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>{value}</div>
          </div>
        ))}
      </div>

      {rawEntries.length > 0 && (
        <div>
          <button
            className="btn btn-outline btn-sm"
            onClick={() => setShowAll((v) => !v)}
            style={{ marginBottom: showAll ? "0.5rem" : 0 }}
          >
            {showAll ? "Hide" : "Show"} all {rawEntries.length} raw metrics
          </button>
          {showAll && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {rawEntries.map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ fontFamily: "monospace", fontSize: "0.82rem" }}>{k}</td>
                      <td>{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {record.notes && (
        <div style={{ fontSize: "0.88rem", color: "#334155", borderTop: "1px solid var(--border)", paddingTop: "0.4rem" }}>
          {record.notes}
        </div>
      )}
    </div>
  );
}

function QcTab({ patientId }: { patientId: number }) {
  const [records, setRecords] = useState<NgsQcInfo[]>([]);
  const [auditLog, setAuditLog] = useState<VariantAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [qcType, setQcType] = useState<QcType>("panel");
  const [file, setFile] = useState<File | null>(null);
  const [manualForm, setManualForm] = useState({
    median_coverage: "",
    pct_20x: "",
    uniformity_pct: "",
  });
  const [passFail, setPassFail] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchQcRecords(patientId), fetchVariantAudit(patientId)])
      .then(([qc, audit]) => {
        setRecords(qc);
        setAuditLog(audit);
      })
      .finally(() => setLoading(false));
  }, [patientId]);

  const resetForm = () => {
    setQcType("panel");
    setFile(null);
    setManualForm({ median_coverage: "", pct_20x: "", uniformity_pct: "" });
    setPassFail("");
    setNotes("");
    setError(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      let created: NgsQcInfo;
      if (file) {
        created = await uploadQcFile(patientId, file, qcType, {
          pass_fail: passFail || undefined,
          notes: notes || undefined,
        });
      } else {
        const median = manualForm.median_coverage ? parseFloat(manualForm.median_coverage) : null;
        const pct20 = manualForm.pct_20x ? parseFloat(manualForm.pct_20x) : null;
        const uni = manualForm.uniformity_pct ? parseFloat(manualForm.uniformity_pct) : null;
        if (median == null && pct20 == null && uni == null) {
          throw new Error("Provide a file or fill at least one metric");
        }
        created = await createQcRecord(patientId, {
          qc_type: qcType,
          median_coverage: median,
          pct_20x: pct20,
          uniformity_pct: uni,
          pass_fail: passFail || null,
          notes: notes || null,
        });
      }
      setRecords((prev) => [created, ...prev]);
      setShowForm(false);
      resetForm();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save QC record");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (qcId: number) => {
    if (!confirm("Delete this QC record?")) return;
    try {
      await deleteQcRecord(qcId);
      setRecords((prev) => prev.filter((r) => r.id !== qcId));
    } catch {
      alert("Failed to delete QC record");
    }
  };

  if (loading) return <p className="text-muted" style={{ marginTop: "1rem" }}>Loading QC data…</p>;

  return (
    <div style={{ marginTop: "0.75rem" }}>
      <div className="flex-between mb-1">
        <strong style={{ fontSize: "1rem" }}>QC Metrics</strong>
        {!showForm && (
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm(true)}>
            + Add QC Record
          </button>
        )}
      </div>

      {showForm && (
        <div className="card" style={{ padding: "1rem", marginBottom: "1rem", border: "1px solid var(--primary)" }}>
          <div className="flex-between mb-1">
            <strong>New QC Record</strong>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-success btn-sm" onClick={handleSave} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => {
                  setShowForm(false);
                  resetForm();
                }}
              >
                Cancel
              </button>
            </div>
          </div>
          {error && <div className="alert alert-danger mb-1">{error}</div>}

          <div style={{ marginBottom: "0.75rem" }}>
            <label className="form-label">QC Type</label>
            <div style={{ display: "flex", gap: "1rem" }}>
              {(["panel", "exome"] as QcType[]).map((t) => (
                <label key={t} style={{ display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer" }}>
                  <input
                    type="radio"
                    name="qc_type"
                    checked={qcType === t}
                    onChange={() => setQcType(t)}
                  />
                  <span style={{ textTransform: "capitalize" }}>{t}</span>
                  <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
                    {t === "panel" ? "(panel-of-genes)" : "(whole-exome, ~42 Mb)"}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: "0.75rem" }}>
            <label className="form-label">Upload QC file (CSV / TSV)</label>
            <input
              type="file"
              accept=".csv,.tsv,.txt"
              className="form-control"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <p style={{ fontSize: "0.78rem", color: "var(--muted)", marginTop: "0.25rem" }}>
              Two-column (metric, value) or two-row (header, values) layout. The three report
              metrics are auto-extracted; every row is preserved for analysis.
            </p>
          </div>

          {!file && (
            <>
              <div style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "0.4rem" }}>
                — or fill manually —
              </div>
              <div className="row" style={{ gap: "0.75rem", marginBottom: "0.75rem" }}>
                {[
                  { key: "median_coverage", label: "Median Coverage" },
                  { key: "pct_20x", label: "% of target ≥20X" },
                  { key: "uniformity_pct", label: "Uniformity (%)" },
                ].map(({ key, label }) => (
                  <div key={key} style={{ flex: "1 1 160px" }}>
                    <label className="form-label">{label}</label>
                    <input
                      type="number"
                      step="any"
                      className="form-control"
                      value={(manualForm as Record<string, string>)[key]}
                      onChange={(e) =>
                        setManualForm((f) => ({ ...f, [key]: e.target.value }))
                      }
                    />
                  </div>
                ))}
              </div>
            </>
          )}

          <div className="row" style={{ gap: "0.75rem" }}>
            <div style={{ flex: "1 1 160px" }}>
              <label className="form-label">Pass / Fail</label>
              <select
                className="form-control"
                value={passFail}
                onChange={(e) => setPassFail(e.target.value)}
              >
                <option value="">— Select —</option>
                <option value="PASS">PASS</option>
                <option value="FAIL">FAIL</option>
                <option value="BORDERLINE">BORDERLINE</option>
              </select>
            </div>
            <div style={{ flex: "1 1 100%" }}>
              <label className="form-label">Notes</label>
              <textarea
                className="form-control"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {records.length === 0 ? (
        <p className="text-muted">No QC records for this patient.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {records.map((r) => (
            <QcRecordCard key={r.id} record={r} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <hr />

      <strong style={{ fontSize: "1rem" }}>Variant Audit Log</strong>
      <p style={{ fontSize: "0.82rem", color: "var(--muted)", marginBottom: "0.75rem" }}>
        Records every change to classification, IGV review status, and review comments.
      </p>

      {auditLog.length === 0 ? (
        <p className="text-muted">No audit entries yet. Changes to variant classification fields will appear here.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>User</th>
                <th>Variant</th>
                <th>Field</th>
                <th>From</th>
                <th>To</th>
              </tr>
            </thead>
            <tbody>
              {auditLog.map((e) => (
                <tr key={e.id}>
                  <td style={{ whiteSpace: "nowrap", fontSize: "0.82rem", color: "var(--muted)" }}>
                    {e.changed_at?.replace("T", " ").slice(0, 16) ?? "—"}
                  </td>
                  <td style={{ fontWeight: 600 }}>{e.changed_by}</td>
                  <td>
                    <span
                      style={{
                        fontSize: "0.75rem",
                        padding: "0.1em 0.4em",
                        borderRadius: "0.25rem",
                        background: e.variant_type === "singleton" ? "#dbeafe" : "#ede9fe",
                        color: e.variant_type === "singleton" ? "#1d4ed8" : "#6d28d9",
                        fontWeight: 600,
                        marginRight: "0.3rem",
                      }}
                    >
                      {e.variant_type}
                    </span>
                    #{e.variant_id}
                  </td>
                  <td>
                    <code style={{ fontSize: "0.82rem" }}>{e.field_name}</code>
                  </td>
                  <td style={{ color: "var(--danger)", fontSize: "0.88rem" }}>
                    {e.old_value ?? <em style={{ color: "var(--muted)" }}>none</em>}
                  </td>
                  <td style={{ color: "var(--success)", fontSize: "0.88rem" }}>
                    {e.new_value ?? <em style={{ color: "var(--muted)" }}>none</em>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Files tab ─────────────────────────────────────────────────────────────

function FilesTab({ patient }: { patient: PatientInfo }) {
  const vcf = patient.vcf_files ?? [];
  const uploads: VariantUploadInfo[] = patient.variant_uploads ?? [];

  return (
    <div style={{ marginTop: "0.75rem" }}>
      <strong style={{ display: "block", marginBottom: "0.5rem" }}>VCF Files</strong>
      {vcf.length === 0 ? (
        <p className="text-muted">No VCF files uploaded.</p>
      ) : (
        <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Size</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {vcf.map((f) => (
                <tr key={f.id}>
                  <td>{f.filename}</td>
                  <td>{f.file_size != null ? `${(f.file_size / 1024 / 1024).toFixed(1)} MB` : "—"}</td>
                  <td>{f.uploaded_at?.slice(0, 10) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <strong style={{ display: "block", marginBottom: "0.5rem" }}>Variant Uploads</strong>
      {uploads.length === 0 ? (
        <p className="text-muted">No variant spreadsheets uploaded.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>Size</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((u) => (
                <tr key={u.id}>
                  <td>{u.original_filename}</td>
                  <td>{u.file_type}</td>
                  <td>{u.file_size != null ? `${(u.file_size / 1024).toFixed(0)} KB` : "—"}</td>
                  <td>{u.uploaded_at?.slice(0, 10) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Terms tab ─────────────────────────────────────────────────────────────

function TermsTab({
  patient,
  onHpoRemoved,
}: {
  patient: PatientInfo;
  onHpoRemoved: (termId: number) => void;
}) {
  const [diseaseTerms, setDiseaseTerms] = useState<DiseaseTerm[]>([]);
  const [dtLoaded, setDtLoaded] = useState(false);

  useEffect(() => {
    fetchPatientDiseaseTerms(patient.id)
      .then(setDiseaseTerms)
      .finally(() => setDtLoaded(true));
  }, [patient.id]);

  const removeHpoTerm = async (termId: number) => {
    if (!confirm("Remove this HPO term from the patient?")) return;
    await removeHPO(patient.id, termId);
    onHpoRemoved(termId);
  };

  const removeDt = async (termId: number) => {
    if (!confirm("Remove this disease term from the patient?")) return;
    await removePatientDiseaseTerm(patient.id, termId);
    setDiseaseTerms((prev) => prev.filter((t) => t.id !== termId));
  };

  return (
    <div style={{ marginTop: "0.75rem" }}>
      <strong style={{ display: "block", marginBottom: "0.5rem" }}>HPO Terms</strong>
      {patient.hpo_terms.length === 0 ? (
        <p className="text-muted">No HPO terms assigned.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, marginBottom: "1.5rem" }}>
          {patient.hpo_terms.map((t) => (
            <li
              key={t.id}
              className="flex-between"
              style={{ padding: "0.45rem 0.75rem", borderBottom: "1px solid var(--border)" }}
            >
              <span>
                <strong>{t.hpo_id}</strong> — {t.term_name}
              </span>
              <button className="btn btn-outline-danger btn-sm" onClick={() => removeHpoTerm(t.id)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <strong style={{ display: "block", marginBottom: "0.5rem" }}>Disease Terms</strong>
      {!dtLoaded ? (
        <p className="text-muted">Loading…</p>
      ) : diseaseTerms.length === 0 ? (
        <p className="text-muted">No disease terms assigned.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {diseaseTerms.map((t) => (
            <li
              key={t.id}
              className="flex-between"
              style={{ padding: "0.45rem 0.75rem", borderBottom: "1px solid var(--border)" }}
            >
              <span>{t.term_name}</span>
              <button className="btn btn-outline-danger btn-sm" onClick={() => removeDt(t.id)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [patient, setPatient] = useState<PatientInfo | null>(null);
  const [error, setError] = useState(false);
  const validTabs: Tab[] = ["overview", "variants", "qc", "files", "terms"];
  const urlTab = searchParams.get("tab") as Tab | null;
  const [tab, setTab] = useState<Tab>(validTabs.includes(urlTab as Tab) ? (urlTab as Tab) : "overview");

  const handleSetTab = useCallback((newTab: Tab) => {
    setTab(newTab);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (newTab === "overview") {
        next.delete("tab");
      } else {
        next.set("tab", newTab);
      }
      return next;
    });
  }, [setSearchParams]);

  // Patient edit state
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      fetchPatient(Number(id))
        .then(setPatient)
        .catch(() => setError(true));
    }
  }, [id]);

  const startEditing = useCallback(() => {
    if (!patient) return;
    setSaveError(null);
    setForm({
      name: patient.name ?? "",
      hkid: patient.hkid ?? "",
      dob: patient.dob ?? "",
      sex: patient.sex ?? "",
      age: patient.age != null ? String(patient.age) : "",
      age_unit: patient.age_unit ?? "",
      ethnicity: patient.ethnicity ?? "",
      im_lab_number: patient.im_lab_number ?? "",
      clinical_history: patient.clinical_history ?? patient.case_history ?? "",
      type_of_test: patient.type_of_test ?? "",
      type_of_findings: patient.type_of_findings ?? "",
      findings_summary: patient.findings_summary ?? "",
      request_dr: patient.request_dr ?? "",
      remark: patient.remark ?? "",
      report_date: patient.report_date ?? "",
      specimen_collected: patient.specimen_collected ?? "",
      specimen_arrived: patient.specimen_arrived ?? "",
      ngs_batch: patient.ngs_batch ?? "",
      ngs_tat: patient.ngs_tat ?? "",
      ngs_tat_final: patient.ngs_tat_final ?? "",
    });
    setEditing(true);
  }, [patient]);

  const savePatient = async () => {
    if (!patient) return;
    setSaving(true);
    setSaveError(null);
    try {
      const payload: Partial<PatientInfo> = {
        name: form.name || null,
        hkid: form.hkid || null,
        dob: form.dob || null,
        sex: form.sex || null,
        age: form.age || null,
        age_unit: form.age_unit || null,
        ethnicity: form.ethnicity || null,
        im_lab_number: form.im_lab_number || null,
        clinical_history: form.clinical_history || null,
        type_of_test: form.type_of_test || null,
        type_of_findings: form.type_of_findings || null,
        findings_summary: form.findings_summary || null,
        request_dr: form.request_dr || null,
        remark: form.remark || null,
        report_date: form.report_date || null,
        specimen_collected: form.specimen_collected || null,
        specimen_arrived: form.specimen_arrived || null,
        ngs_batch: form.ngs_batch || null,
        ngs_tat: form.ngs_tat || null,
        ngs_tat_final: form.ngs_tat_final || null,
      };
      const updated = await updatePatient(patient.id, payload);
      setPatient((prev) =>
        prev ? { ...updated, singletons: prev.singletons, trios: prev.trios, vcf_files: prev.vcf_files, variant_uploads: prev.variant_uploads } : updated
      );
      setEditing(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to update patient");
    } finally {
      setSaving(false);
    }
  };

  const handleVariantUpdated = useCallback((updated: VariantRow) => {
    setPatient((prev) => {
      if (!prev) return prev;
      if (updated._type === "singleton") {
        return {
          ...prev,
          singletons: (prev.singletons ?? []).map((s) =>
            s.id === updated.id ? updated : s
          ),
        };
      } else {
        return {
          ...prev,
          trios: (prev.trios ?? []).map((t) =>
            t.id === updated.id ? updated : t
          ),
        };
      }
    });
  }, []);

  if (error) return <div className="alert alert-danger">Patient not found.</div>;
  if (!patient) return <p className="text-muted">Loading patient data…</p>;

  const variants: VariantRow[] = [
    ...(patient.singletons ?? []).map((s) => ({ ...s, _type: "singleton" as const })),
    ...(patient.trios ?? []).map((t) => ({ ...t, _type: "trio" as const })),
  ];

  const variantCount = variants.length;
  const vcfCount = (patient.vcf_files ?? []).length;
  const hpoCount = patient.hpo_terms.length;

  return (
    <>
      <div className="flex-between">
        <div>
          <h2 style={{ marginBottom: "0.1rem" }}>{patient.name ?? patient.lab_number}</h2>
          <p className="text-muted" style={{ fontSize: "0.88rem" }}>
            Lab: <code>{patient.lab_number}</code>
            {patient.ngs_batch && (
              <span style={{ marginLeft: "1rem" }}>Batch: <code>{patient.ngs_batch}</code></span>
            )}
          </p>
        </div>
        <Link to="/select" className="btn btn-outline-secondary btn-sm">
          ← Back to list
        </Link>
      </div>

      <div className="tabs" style={{ marginTop: "0.75rem" }}>
        {(
          [
            { key: "overview", label: "Overview" },
            { key: "variants", label: `Variants (${variantCount})` },
            { key: "qc", label: "QC & Audit" },
            { key: "files", label: `Files (${vcfCount})` },
            { key: "terms", label: `Terms (${hpoCount})` },
          ] as { key: Tab; label: string }[]
        ).map(({ key, label }) => (
          <button
            key={key}
            className={`tab${tab === key ? " tab-active" : ""}`}
            onClick={() => handleSetTab(key as Tab)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <OverviewTab
          patient={patient}
          editing={editing}
          form={form}
          saving={saving}
          saveError={saveError}
          onStartEdit={startEditing}
          onFieldChange={(k, v) => setForm((f) => ({ ...f, [k]: v }))}
          onSave={savePatient}
          onCancelEdit={() => setEditing(false)}
        />
      )}

      {tab === "variants" && (
        <VariantsTab variants={variants} onVariantUpdated={handleVariantUpdated} />
      )}

      {tab === "qc" && <QcTab patientId={patient.id} />}

      {tab === "files" && <FilesTab patient={patient} />}

      {tab === "terms" && (
        <TermsTab
          patient={patient}
          onHpoRemoved={(termId) =>
            setPatient((prev) =>
              prev
                ? { ...prev, hpo_terms: prev.hpo_terms.filter((t) => t.id !== termId) }
                : prev
            )
          }
        />
      )}
    </>
  );
}
