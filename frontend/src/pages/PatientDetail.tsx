import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchPatient, removeHPO, updatePatient } from "../api/client";
import type { PatientInfo } from "../types";

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const [patient, setPatient] = useState<PatientInfo | null>(null);
  const [error, setError] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});

  useEffect(() => {
    if (id) {
      fetchPatient(Number(id))
        .then(setPatient)
        .catch(() => setError(true));
    }
  }, [id]);

  const handleRemove = async (termId: number) => {
    if (!patient || !confirm("Remove this HPO term from the patient?")) return;
    await removeHPO(patient.id, termId);
    setPatient({
      ...patient,
      hpo_terms: patient.hpo_terms.filter((t) => t.id !== termId),
    });
  };

  if (error) {
    return <div className="alert alert-danger">Patient not found.</div>;
  }
  if (!patient) {
    return <p className="text-muted">Loading patient data…</p>;
  }

  const startEditing = () => {
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
  };

  const onFieldChange = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

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
      setPatient(updated);
      setEditing(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to update patient";
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="flex-between">
        <div>
          <h2>{patient.name ?? patient.lab_number}</h2>
          <p className="text-muted">
            Lab Number: <code>{patient.lab_number}</code>
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {!editing ? (
            <button className="btn btn-primary btn-sm" onClick={startEditing}>
              Edit Patient
            </button>
          ) : (
            <>
              <button
                className="btn btn-success btn-sm"
                onClick={savePatient}
                disabled={saving}
              >
                {saving ? "Saving..." : "Save"}
              </button>
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => setEditing(false)}
                disabled={saving}
              >
                Cancel
              </button>
            </>
          )}
          <Link to="/select" className="btn btn-outline-secondary btn-sm">
            ← Back to list
          </Link>
        </div>
      </div>

      {saveError ? (
        <div className="alert alert-danger mt-1">{saveError}</div>
      ) : null}

      {editing ? (
        <div className="card" style={{ marginTop: "0.75rem", padding: "1rem" }}>
          <h3 className="mb-1">Edit Patient Information</h3>
          <div className="row" style={{ gap: "0.75rem" }}>
            <div style={{ flex: "1 1 220px" }}>
              <label className="form-label">Name</label>
              <input
                className="form-control"
                value={form.name ?? ""}
                onChange={(e) => onFieldChange("name", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 220px" }}>
              <label className="form-label">HKID</label>
              <input
                className="form-control"
                value={form.hkid ?? ""}
                onChange={(e) => onFieldChange("hkid", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 180px" }}>
              <label className="form-label">DOB</label>
              <input
                type="date"
                className="form-control"
                value={form.dob ?? ""}
                onChange={(e) => onFieldChange("dob", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 140px" }}>
              <label className="form-label">Sex</label>
              <input
                className="form-control"
                value={form.sex ?? ""}
                onChange={(e) => onFieldChange("sex", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 120px" }}>
              <label className="form-label">Age</label>
              <input
                className="form-control"
                value={form.age ?? ""}
                onChange={(e) => onFieldChange("age", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 140px" }}>
              <label className="form-label">Age Unit</label>
              <input
                className="form-control"
                value={form.age_unit ?? ""}
                onChange={(e) => onFieldChange("age_unit", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 220px" }}>
              <label className="form-label">Ethnicity</label>
              <input
                className="form-control"
                value={form.ethnicity ?? ""}
                onChange={(e) => onFieldChange("ethnicity", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 220px" }}>
              <label className="form-label">IM Lab Number</label>
              <input
                className="form-control"
                value={form.im_lab_number ?? ""}
                onChange={(e) => onFieldChange("im_lab_number", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 260px" }}>
              <label className="form-label">Type of Test</label>
              <input
                className="form-control"
                value={form.type_of_test ?? ""}
                onChange={(e) => onFieldChange("type_of_test", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 260px" }}>
              <label className="form-label">Type of Findings</label>
              <input
                className="form-control"
                value={form.type_of_findings ?? ""}
                onChange={(e) =>
                  onFieldChange("type_of_findings", e.target.value)
                }
              />
            </div>
            <div style={{ flex: "1 1 220px" }}>
              <label className="form-label">Request Dr</label>
              <input
                className="form-control"
                value={form.request_dr ?? ""}
                onChange={(e) => onFieldChange("request_dr", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 180px" }}>
              <label className="form-label">Report Date</label>
              <input
                type="date"
                className="form-control"
                value={form.report_date ?? ""}
                onChange={(e) => onFieldChange("report_date", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 200px" }}>
              <label className="form-label">Specimen Collected</label>
              <input
                type="date"
                className="form-control"
                value={form.specimen_collected ?? ""}
                onChange={(e) =>
                  onFieldChange("specimen_collected", e.target.value)
                }
              />
            </div>
            <div style={{ flex: "1 1 200px" }}>
              <label className="form-label">Specimen Arrived</label>
              <input
                type="date"
                className="form-control"
                value={form.specimen_arrived ?? ""}
                onChange={(e) =>
                  onFieldChange("specimen_arrived", e.target.value)
                }
              />
            </div>
            <div style={{ flex: "1 1 180px" }}>
              <label className="form-label">NGS Batch</label>
              <input
                className="form-control"
                value={form.ngs_batch ?? ""}
                onChange={(e) => onFieldChange("ngs_batch", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 140px" }}>
              <label className="form-label">NGS TAT</label>
              <input
                className="form-control"
                value={form.ngs_tat ?? ""}
                onChange={(e) => onFieldChange("ngs_tat", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 180px" }}>
              <label className="form-label">NGS TAT Final</label>
              <input
                className="form-control"
                value={form.ngs_tat_final ?? ""}
                onChange={(e) => onFieldChange("ngs_tat_final", e.target.value)}
              />
            </div>
            <div style={{ flex: "1 1 100%" }}>
              <label className="form-label">Clinical History</label>
              <textarea
                className="form-control"
                rows={3}
                value={form.clinical_history ?? ""}
                onChange={(e) =>
                  onFieldChange("clinical_history", e.target.value)
                }
              />
            </div>
            <div style={{ flex: "1 1 100%" }}>
              <label className="form-label">Findings Summary</label>
              <textarea
                className="form-control"
                rows={2}
                value={form.findings_summary ?? ""}
                onChange={(e) =>
                  onFieldChange("findings_summary", e.target.value)
                }
              />
            </div>
            <div style={{ flex: "1 1 100%" }}>
              <label className="form-label">Remark</label>
              <textarea
                className="form-control"
                rows={2}
                value={form.remark ?? ""}
                onChange={(e) => onFieldChange("remark", e.target.value)}
              />
            </div>
          </div>
        </div>
      ) : null}

      <hr />

      <div className="row">
        {/* Patient Demographics */}
        <div className="col-2">
          <h3 className="mb-1">Patient Demographics</h3>
          <div className="table-wrap">
            <table>
              <tbody>
                <tr>
                  <th>Name</th>
                  <td>{patient.name ?? "—"}</td>
                </tr>
                <tr>
                  <th>HKID</th>
                  <td>{patient.hkid ?? "—"}</td>
                </tr>
                <tr>
                  <th>Date of Birth</th>
                  <td>{patient.dob ?? "—"}</td>
                </tr>
                <tr>
                  <th>Sex</th>
                  <td>{patient.sex ?? "—"}</td>
                </tr>
                <tr>
                  <th>Age</th>
                  <td>
                    {patient.age != null
                      ? `${patient.age} ${patient.age_unit ?? ""}`
                      : "—"}
                  </td>
                </tr>
                <tr>
                  <th>Ethnicity</th>
                  <td>{patient.ethnicity ?? "—"}</td>
                </tr>
                <tr>
                  <th>IM Lab Number</th>
                  <td>{patient.im_lab_number ?? "—"}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3 className="mt-2 mb-1">Clinical Information</h3>
          <div className="table-wrap">
            <table>
              <tbody>
                <tr>
                  <th>Clinical History</th>
                  <td>
                    {patient.clinical_history ?? patient.case_history ?? "—"}
                  </td>
                </tr>
                <tr>
                  <th>Type of Test</th>
                  <td>{patient.type_of_test ?? "—"}</td>
                </tr>
                <tr>
                  <th>Type of Findings</th>
                  <td>{patient.type_of_findings ?? "—"}</td>
                </tr>
                <tr>
                  <th>Findings Summary</th>
                  <td>{patient.findings_summary ?? "—"}</td>
                </tr>
                <tr>
                  <th>Request Dr</th>
                  <td>{patient.request_dr ?? "—"}</td>
                </tr>
                <tr>
                  <th>Remark</th>
                  <td>{patient.remark ?? "—"}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3 className="mt-2 mb-1">Report / NGS Info</h3>
          <div className="table-wrap">
            <table>
              <tbody>
                <tr>
                  <th>Report Date</th>
                  <td>{patient.report_date ?? "—"}</td>
                </tr>
                <tr>
                  <th>Specimen Collected</th>
                  <td>{patient.specimen_collected ?? "—"}</td>
                </tr>
                <tr>
                  <th>Specimen Arrived</th>
                  <td>{patient.specimen_arrived ?? "—"}</td>
                </tr>
                <tr>
                  <th>NGS Batch</th>
                  <td>{patient.ngs_batch ?? "—"}</td>
                </tr>
                <tr>
                  <th>NGS TAT</th>
                  <td>{patient.ngs_tat ?? "—"}</td>
                </tr>
                <tr>
                  <th>NGS TAT Final</th>
                  <td>{patient.ngs_tat_final ?? "—"}</td>
                </tr>
                <tr>
                  <th>Created</th>
                  <td>{patient.created_at ?? "—"}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* HPO Terms + Singletons */}
        <div className="col-2">
          <h3 className="mb-1">Associated HPO Terms</h3>
          {patient.hpo_terms.length === 0 ? (
            <p className="text-muted">No HPO terms assigned.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0 }}>
              {patient.hpo_terms.map((t) => (
                <li
                  key={t.id}
                  className="flex-between"
                  style={{
                    padding: "0.5rem 0.75rem",
                    borderBottom: `1px solid var(--border)`,
                  }}
                >
                  <span>
                    <strong>{t.hpo_id}</strong> — {t.term_name}
                  </span>
                  <button
                    className="btn btn-outline-danger btn-sm"
                    onClick={() => handleRemove(t.id)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}

          <h3 className="mt-2 mb-1">Singleton Findings</h3>
          {!patient.singletons || patient.singletons.length === 0 ? (
            <p className="text-muted">No singleton findings recorded.</p>
          ) : (
            patient.singletons.map((s) => (
              <div
                className="card mb-1"
                key={s.id}
                style={{ padding: "0.75rem" }}
              >
                <p>
                  <strong>Gene:</strong> {s.gene_names ?? "—"} &nbsp;
                  <strong>Classification:</strong> {s.classification ?? "—"}
                </p>
                <p>
                  <strong>Variant:</strong> {s.reportable_variant ?? "—"} &nbsp;
                  <strong>Chr:Pos:</strong> {s.chr_pos ?? "—"} &nbsp;
                  <strong>Ref/Alt:</strong> {s.ref_alt ?? "—"}
                </p>
                <p>
                  <strong>HGVS c.:</strong> {s.hgvs_c ?? "—"} &nbsp;
                  <strong>HGVS p.:</strong> {s.hgvs_p ?? "—"} &nbsp;
                  <strong>Exon:</strong> {s.exon_number ?? "—"}
                </p>
                <p>
                  <strong>Zygosity:</strong> {s.zygosity ?? "—"} &nbsp;
                  <strong>Inheritance:</strong> {s.inheritance ?? "—"} &nbsp;
                  <strong>Inherited From:</strong> {s.inherited_from ?? "—"}
                </p>
                <p>
                  <strong>OMIM:</strong> {s.omim_id ?? "—"} &nbsp;
                  <strong>RSID:</strong> {s.rsid ?? "—"} &nbsp;
                  <strong>Title:</strong> {s.title ?? "—"}
                </p>
                <p>
                  <strong>IGV Review:</strong> {s.igv_review ? "Yes" : "No"}{" "}
                  &nbsp;
                  <strong>Comment:</strong> {s.second_review_comment ?? "—"}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
