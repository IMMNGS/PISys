import { useState, useCallback, useEffect } from "react";
import { useLocation } from "react-router-dom";
import {
  fetchReportPreview,
  downloadReport,
  downloadSingleGeneReport,
  fetchPatientOptions,
  updateSingleton,
  updateTrio,
  type ReportPreview,
} from "../api/client";
import SearchableSelect from "../components/SearchableSelect";

type TestType = "singleton" | "trio";
const DEFAULT_VARIANT_ROWS = 20;

export default function Report() {
  const [labNumber, setLabNumber] = useState("");
  const [testType, setTestType] = useState<TestType>("singleton");
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatingSingleGene, setGeneratingSingleGene] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoLoadFromParams, setAutoLoadFromParams] = useState(false);
  const [showAllVariants, setShowAllVariants] = useState(false);
  const [editableReportableVariants, setEditableReportableVariants] = useState<
    Record<number, string>
  >({});
  const [savingVariantId, setSavingVariantId] = useState<number | null>(null);

  const location = useLocation();

  // Editable text fields
  const [interpretation, setInterpretation] = useState("");
  const [comments, setComments] = useState("");
  const [variantClassification, setVariantClassification] = useState("");
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

  const handlePreview = useCallback(async () => {
    if (!labNumber.trim()) return;
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const data = await fetchReportPreview(labNumber.trim(), testType);
      setPreview(data);
      setShowAllVariants(false);
      setEditableReportableVariants(
        Object.fromEntries(
          data.variants.map((v) => [v.id, v.reportable_variant ?? ""]),
        ),
      );
      setTestProcess(data.defaults.test_process);
      setDisclaimer(data.defaults.disclaimer);
      setReferences(data.defaults.references);
      setInterpretation("");
      setComments("");
      setVariantClassification("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [labNumber, testType]);

  // Parse query params for automatic behaviour
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const ln = params.get("lab_number");
    const tt = params.get("test_type");
    const auto = params.get("auto_preview");
    if (ln) setLabNumber(ln);
    if (tt === "trio" || tt === "singleton") setTestType(tt as TestType);
    // Only auto-load preview when explicitly requested by the navigator
    if (ln && auto === "1") setAutoLoadFromParams(true);
  }, [location.search]);

  // When params set labNumber/testType, auto-load preview
  useEffect(() => {
    if (autoLoadFromParams && labNumber.trim()) {
      // call preview and then clear flag to avoid repeated calls
      handlePreview();
      setAutoLoadFromParams(false);
    }
  }, [autoLoadFromParams, labNumber, handlePreview]);

  // (no automatic download) After preview loads we do nothing — user must click Generate

  const handleGenerate = async () => {
    if (!preview) return;
    setGenerating(true);
    setError(null);
    try {
      await downloadReport({
        lab_number: labNumber.trim(),
        test_type: testType,
        interpretation,
        comments,
        variant_classification: variantClassification,
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

  const handleGenerateSingleGene = async () => {
    if (!labNumber.trim()) return;
    setGeneratingSingleGene(true);
    setError(null);
    try {
      await downloadSingleGeneReport(labNumber.trim());
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Single-gene report generation failed",
      );
    } finally {
      setGeneratingSingleGene(false);
    }
  };

  const handleReportableVariantSave = async (variantId: number) => {
    const value = (editableReportableVariants[variantId] ?? "").trim();
    setSavingVariantId(variantId);
    setError(null);
    try {
      if (testType === "trio") {
        await updateTrio(variantId, {
          reportable_variant: value || null,
        });
      } else {
        await updateSingleton(variantId, {
          reportable_variant: value || null,
        });
      }

      setPreview((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          variants: prev.variants.map((v) =>
            v.id === variantId
              ? { ...v, reportable_variant: value || null }
              : v,
          ),
        };
      });
    } catch (e: unknown) {
      setError(
        e instanceof Error
          ? `Failed to save reportable variant: ${e.message}`
          : "Failed to save reportable variant",
      );
    } finally {
      setSavingVariantId(null);
    }
  };

  const patient = preview?.patient;
  const variants = preview?.variants ?? [];
  const visibleVariants = showAllVariants
    ? variants
    : variants.slice(0, DEFAULT_VARIANT_ROWS);
  const hasMoreVariants = variants.length > DEFAULT_VARIANT_ROWS;

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
          <button
            className="btn btn-outline mt-1"
            disabled={generatingSingleGene || loading || !labNumber.trim()}
            onClick={handleGenerateSingleGene}
            style={{ marginLeft: "0.75rem" }}
          >
            {generatingSingleGene
              ? "Generating…"
              : "Download Single-Gene Report (.docx)"}
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
                <strong>Clinical History:</strong>{" "}
                {patient.clinical_history || patient.case_history || "—"}
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
            <div className="card-body" style={{ paddingBottom: 0 }}>
              {hasMoreVariants && (
                <button
                  className="btn btn-outline"
                  onClick={() => setShowAllVariants((prev) => !prev)}
                  style={{ marginBottom: "0.75rem" }}
                >
                  {showAllVariants
                    ? `Show first ${DEFAULT_VARIANT_ROWS}`
                    : `Show all (${variants.length})`}
                </button>
              )}
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
                    <th>Reportable Variant</th>
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
                        colSpan={12}
                        className="text-muted"
                        style={{ textAlign: "center" }}
                      >
                        No variants found for this patient.
                      </td>
                    </tr>
                  ) : (
                    visibleVariants.map((v) => {
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
                          <td>
                            <input
                              type="text"
                              className="form-control"
                              value={editableReportableVariants[v.id] ?? ""}
                              onChange={(e) =>
                                setEditableReportableVariants((prev) => ({
                                  ...prev,
                                  [v.id]: e.target.value,
                                }))
                              }
                              onBlur={() => {
                                const original = v.reportable_variant ?? "";
                                const edited =
                                  editableReportableVariants[v.id] ?? "";
                                if (edited !== original) {
                                  handleReportableVariantSave(v.id);
                                }
                              }}
                              disabled={savingVariantId === v.id}
                              placeholder="e.g. C / A / I / N"
                              style={{ minWidth: "9rem" }}
                            />
                          </td>
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
            <div className="card-header">
              Interpretation / Recommended Action
            </div>
            <div className="card-body">
              <textarea
                className="form-control"
                rows={5}
                value={interpretation}
                onChange={(e) => setInterpretation(e.target.value)}
                placeholder="Enter interpretation / recommended action..."
              />
            </div>
          </div>

          <div className="card mb-2">
            <div className="card-header">Comments</div>
            <div className="card-body">
              <textarea
                className="form-control"
                rows={4}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="Enter additional comments..."
              />
            </div>
          </div>

          <div className="card mb-2">
            <div className="card-header">Variant Classification</div>
            <div className="card-body">
              <textarea
                className="form-control"
                rows={4}
                value={variantClassification}
                onChange={(e) => setVariantClassification(e.target.value)}
                placeholder="Enter variant classification notes..."
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
          <div
            className="flex-gap"
            style={{ justifyContent: "flex-end", marginBottom: "2rem" }}
          >
            <button
              className="btn btn-primary"
              disabled={generating || generatingSingleGene}
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
