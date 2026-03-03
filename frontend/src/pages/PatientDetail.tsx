import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchPatient, removeHPO } from "../api/client";
import type { PatientInfo } from "../types";

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const [patient, setPatient] = useState<PatientInfo | null>(null);
  const [error, setError] = useState(false);

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

  return (
    <>
      <div className="flex-between">
        <div>
          <h2>{patient.name ?? patient.lab_number}</h2>
          <p className="text-muted">
            Lab Number: <code>{patient.lab_number}</code>
          </p>
        </div>
        <Link to="/patients" className="btn btn-outline-secondary btn-sm">
          ← Back to list
        </Link>
      </div>

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
                  <td>{patient.clinical_history ?? patient.case_history ?? "—"}</td>
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
