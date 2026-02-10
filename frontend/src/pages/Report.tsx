import { useState, useCallback } from "react";
import {
  fetchReportPreview,
  downloadReport,
  fetchPatientOptions,
  type ReportPreview,
} from "../api/client";
import SearchableSelect from "../components/SearchableSelect";

type TestType = "singleton" | "trio";

export default function Report() {
  const [labNumber, setLabNumber] = useState("");
  const [testType, setTestType] = useState<TestType>("singleton");
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Editable text fields
  const [conclusion, setConclusion] = useState("");
  const [testProcess, setTestProcess] = useState("");
  const [disclaimer, setDisclaimer] = useState("");
  const [references, setReferences] = useState("");

  const fetchLabNumbers = useCallback(
    async (search: string, limit: number, offset: number) => {
      const result = await fetchPatientOptions(search, limit, offset);
      return {
        items: result.items
          .map((p) => p.lab_number)
          .filter((ln): ln is string => !!ln),
        total: result.total,
      };
    },
    [],
  );

  const handlePreview = async () => {
    if (!labNumber.trim()) return;
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const data = await fetchReportPreview(labNumber.trim(), testType);
      setPreview(data);
      setTestProcess(data.defaults.test_process);
      setDisclaimer(data.defaults.disclaimer);
      setReferences(data.defaults.references);
      setConclusion("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!preview) return;
    setGenerating(true);
    setError(null);
    try {
      await downloadReport({
        lab_number: labNumber.trim(),
        test_type: testType,
        conclusion,
        test_process: testProcess,
        disclaimer,
        references,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Report generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const patient = preview?.patient;
  const variants = preview?.variants ?? [];

  // Build sex/age display
  const sexAge = patient
    ? (() => {
        let age = "";
        if (patient.age != null) {
          const u = (patient.age_unit || "Y").toUpperCase();
          age = `${patient.age}${u.startsWith("Y") ? "Y" : u.startsWith("M") ? "M" : u.startsWith("D") ? "D" : u}`;
        }
        return age ? `${patient.sex || "—"}/${age}` : patient.sex || "—";
      })()
    : "";

  return (
    <>
      <h2>Generate Report</h2>
      <p className="text-muted mb-2">
        Enter a lab number and select the test type to generate a clinical
        report (.docx).
      </p>

      {/* ── Input: lab number + test type ───────────────────────── */}
      <div className="card mb-2">
        <div className="card-header primary">Report Parameters</div>
        <div className="card-body">
          <div className="row mb-1">
            <div className="col-2">
              <label className="mb-1">
                <strong>Lab Number</strong>
              </label>
              <SearchableSelect
                value={labNumber}
                onChange={setLabNumber}
                fetchOptions={fetchLabNumbers}
                placeholder="Select lab number…"
                itemLabel="lab numbers"
              />
            </div>
            <div className="col-2">
              <label className="mb-1">
                <strong>Test Type</strong>
              </label>
              <div className="flex-gap" style={{ paddingTop: "0.3rem" }}>
                <label style={{ cursor: "pointer" }}>
                  <input
                    type="radio"
                    name="testType"
                    value="singleton"
                    checked={testType === "singleton"}
                    onChange={() => setTestType("singleton")}
                  />{" "}
                  Singleton
                </label>
                <label style={{ cursor: "pointer" }}>
                  <input
                    type="radio"
                    name="testType"
                    value="trio"
                    checked={testType === "trio"}
                    onChange={() => setTestType("trio")}
                  />{" "}
                  Trio
                </label>
              </div>
            </div>
          </div>
          <button
            className="btn btn-primary mt-1"
            disabled={loading || !labNumber.trim()}
            onClick={handlePreview}
          >
            {loading ? "Loading…" : "Load Patient Data"}
          </button>
        </div>
      </div>

      {/* ── Error ──────────────────────────────────────────────── */}
      {error && <div className="alert alert-danger">{error}</div>}

      {/* ── Preview ────────────────────────────────────────────── */}
      {preview && patient && (
        <>
          {/* Patient identity */}
          <div className="card mb-2">
            <div className="card-header">Patient Information</div>
            <div className="card-body">
              <p>
                <strong>Name:</strong> {patient.name || "—"}
              </p>
              <p>
                <strong>Sex/Age:</strong> {sexAge}
              </p>
              <p>
                <strong>HKID:</strong> {patient.hkid || "—"}
              </p>
            </div>
          </div>

          {/* Testing information */}
          <div className="card mb-2">
            <div className="card-header">Testing Information</div>
            <div className="card-body">
              <p>
                <strong>Case History:</strong> {patient.case_history || "—"}
              </p>
              <p>
                <strong>Type of Test:</strong> {patient.type_of_test || "—"}
              </p>
              <p>
                <strong>Specimen Collected:</strong>{" "}
                {patient.specimen_collected || "—"}
              </p>
            </div>
          </div>

          {/* Variant Result table */}
          <div className="card mb-2">
            <div className="card-header">
              Result ({testType === "trio" ? "Trio" : "Singleton"} —{" "}
              {variants.length} variant{variants.length !== 1 ? "s" : ""})
            </div>
            <div
              className="card-body"
              style={{ padding: 0, overflowX: "auto" }}
            >
              <table>
                <thead>
                  <tr>
                    <th>Gene Name / OMIM</th>
                    <th>Transcript / Variant (HGVS)</th>
                    <th>Exon</th>
                    <th>Zygosity</th>
                    <th>Inheritance</th>
                    <th>Parent Origin</th>
                    <th>Classification</th>
                    <th>Position REF/ALT</th>
                    <th>Assembly</th>
                    <th>SNP Identifier</th>
                    <th>Phenotype</th>
                  </tr>
                </thead>
                <tbody>
                  {variants.length === 0 ? (
                    <tr>
                      <td
                        colSpan={11}
                        className="text-muted"
                        style={{ textAlign: "center" }}
                      >
                        No variants found for this patient.
                      </td>
                    </tr>
                  ) : (
                    variants.map((v) => {
                      const geneOmim = [v.gene_names, v.omim_id]
                        .filter(Boolean)
                        .join(" / ");
                      const hgvs = [v.hgvs_c, v.hgvs_p ? `(${v.hgvs_p})` : null]
                        .filter(Boolean)
                        .join(" ");
                      const posRefAlt = [v.chr_pos, v.ref_alt]
                        .filter(Boolean)
                        .join(" ");
                      return (
                        <tr key={v.id}>
                          <td>{geneOmim || "—"}</td>
                          <td>{hgvs || "—"}</td>
                          <td>{v.exon_number || "—"}</td>
                          <td>{v.zygosity || "—"}</td>
                          <td>{v.inheritance || "—"}</td>
                          <td>{v.inherited_from || "—"}</td>
                          <td>{v.classification || "—"}</td>
                          <td>{posRefAlt || "—"}</td>
                          <td>GRCh38/hg38</td>
                          <td>{v.rsid || "—"}</td>
                          <td>{v.title || "—"}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Editable text sections */}
          <div className="card mb-2">
            <div className="card-header">Conclusion</div>
            <div className="card-body">
              <textarea
                className="form-control"
                rows={5}
                value={conclusion}
                onChange={(e) => setConclusion(e.target.value)}
                placeholder="Enter the clinical conclusion for this report..."
              />
            </div>
          </div>

          <div className="card mb-2">
            <div className="card-header">Test Process</div>
            <div className="card-body">
              <textarea
                className="form-control"
                rows={5}
                value={testProcess}
                onChange={(e) => setTestProcess(e.target.value)}
              />
            </div>
          </div>

          <div className="card mb-2">
            <div className="card-header">Disclaimer</div>
            <div className="card-body">
              <textarea
                className="form-control"
                rows={7}
                value={disclaimer}
                onChange={(e) => setDisclaimer(e.target.value)}
              />
            </div>
          </div>

          <div className="card mb-2">
            <div className="card-header">References</div>
            <div className="card-body">
              <textarea
                className="form-control"
                rows={2}
                value={references}
                onChange={(e) => setReferences(e.target.value)}
              />
            </div>
          </div>

          {/* Generate button */}
          <div style={{ textAlign: "right", marginBottom: "2rem" }}>
            <button
              className="btn btn-primary"
              disabled={generating}
              onClick={handleGenerate}
              style={{ fontSize: "1rem", padding: "0.6rem 2rem" }}
            >
              {generating ? "Generating…" : "Download Report (.docx)"}
            </button>
          </div>
        </>
      )}
    </>
  );
}
