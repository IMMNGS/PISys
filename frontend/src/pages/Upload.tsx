import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchPatients,
  fetchPatientOptions as fetchPatientOptionsApi,
  uploadVcfFile,
  uploadSingletonXlsx,
  uploadTrioXlsx,
  uploadQcBulk,
  fetchVcfFiles,
  deleteVcfFile,
} from "../api/client";
import type { PatientInfo, VcfFileInfo, QcType, QcBulkUploadResult } from "../types";
import SearchableSelect from "../components/SearchableSelect";

type UploadType = "vcf" | "singleton" | "trio";

const UPLOAD_LABELS: Record<UploadType, string> = {
  vcf: "VCF File (.vcf, .vcf.gz, .bcf)",
  singleton: "Singleton Variants (.xlsx)",
  trio: "Trio Variants (.xlsx)",
};

const ACCEPT: Record<UploadType, string> = {
  vcf: ".vcf,.gz,.bcf",
  singleton: ".xlsx",
  trio: ".xlsx",
};

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export default function Upload() {
  const [patients, setPatients] = useState<PatientInfo[]>([]);
  const [patientId, setPatientId] = useState<number | "">("");
  const [patientLabel, setPatientLabel] = useState("");
  const [uploadType, setUploadType] = useState<UploadType>("vcf");
  const [status, setStatus] = useState<{
    type: "success" | "error";
    msg: string;
  } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [vcfFiles, setVcfFiles] = useState<VcfFileInfo[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const [refreshKey] = useState(0);
  const [lastUploaded, setLastUploaded] = useState<{
    labNumber?: string;
    testType?: UploadType;
  } | null>(null);

  // QC bulk upload state (no patient required)
  const [qcFile, setQcFile] = useState<File | null>(null);
  const [qcType, setQcType] = useState<QcType>("panel");
  const [qcUploading, setQcUploading] = useState(false);
  const [qcResult, setQcResult] = useState<QcBulkUploadResult | null>(null);
  const [qcError, setQcError] = useState<string | null>(null);

  const navigate = useNavigate();

  const reloadPatients = () => fetchPatients("").then(setPatients);

  useEffect(() => {
    reloadPatients();
  }, []);

  // Map rendered dropdown label -> patient id for resolving selection
  const patientIdMap = useRef<Map<string, number>>(new Map());

  const fetchPatientOptions = useCallback(
    async (search: string, limit: number, offset: number) => {
      const result = await fetchPatientOptionsApi(search, limit, offset);
      for (const p of result.items) {
        const label = `${p.im_lab_number ?? p.lab_number} \u2014 ${p.name ?? "Unnamed"}${p.im_lab_number ? ` (Lab ${p.lab_number})` : ""}`;
        patientIdMap.current.set(label, p.id);
      }
      return {
        items: result.items.map(
          (p) =>
            `${p.im_lab_number ?? p.lab_number} \u2014 ${p.name ?? "Unnamed"}${p.im_lab_number ? ` (Lab ${p.lab_number})` : ""}`,
        ),
        total: result.total,
      };
    },
    [],
  );

  const handlePatientSelect = useCallback((label: string) => {
    setPatientLabel(label);
    if (!label) {
      setPatientId("");
      return;
    }
    const id = patientIdMap.current.get(label);
    setPatientId(id ?? "");
  }, []);

  // Load VCF files when patient changes
  useEffect(() => {
    if (patientId) {
      fetchVcfFiles(patientId).then(setVcfFiles);
    } else {
      setVcfFiles([]);
    }
  }, [patientId]);

  const selectedPatient = patients.find((p) => p.id === patientId);

  const handleUpload = async () => {
    if (!patientId || !fileRef.current?.files?.length) return;
    const file = fileRef.current.files[0];
    setUploading(true);
    setStatus(null);
    try {
      if (uploadType === "vcf") {
        await uploadVcfFile(patientId, file);
        setStatus({ type: "success", msg: `VCF uploaded: ${file.name}` });
        fetchVcfFiles(patientId).then(setVcfFiles);

        // remember last upload for quick report generation
        setLastUploaded({
          labNumber: selectedPatient?.im_lab_number ?? selectedPatient?.lab_number,
          testType: uploadType,
        });
      } else if (uploadType === "singleton") {
        const r = await uploadSingletonXlsx(patientId, file);
        setStatus({ type: "success", msg: r.message });
        setLastUploaded({
          labNumber: selectedPatient?.im_lab_number ?? selectedPatient?.lab_number,
          testType: uploadType,
        });
      } else {
        const r = await uploadTrioXlsx(patientId, file);
        setStatus({ type: "success", msg: r.message });
        setLastUploaded({
          labNumber: selectedPatient?.im_lab_number ?? selectedPatient?.lab_number,
          testType: uploadType,
        });
      }
      if (fileRef.current) fileRef.current.value = "";
    } catch (e: unknown) {
      setStatus({
        type: "error",
        msg: e instanceof Error ? e.message : "Upload failed",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteVcf = async (vcf: VcfFileInfo) => {
    if (!confirm(`Delete ${vcf.filename}?`)) return;
    try {
      await deleteVcfFile(vcf.id);
      setVcfFiles((prev) => prev.filter((v) => v.id !== vcf.id));
      setStatus({
        type: "success",
        msg: `Deleted ${vcf.filename}`,
      });
    } catch {
      setStatus({ type: "error", msg: "Failed to delete VCF file" });
    }
  };

  const handleQcUpload = async () => {
    if (!qcFile) return;
    setQcUploading(true);
    setQcError(null);
    setQcResult(null);
    try {
      const result = await uploadQcBulk(qcFile, qcType);
      setQcResult(result);
    } catch (e: unknown) {
      setQcError(e instanceof Error ? e.message : "QC upload failed");
    } finally {
      setQcUploading(false);
    }
  };

  return (
    <>
      <h2>Upload &amp; Import</h2>
      <p className="text-muted mb-2">
        Upload variant files for existing patients.
      </p>

      {/* ── Status message ─────────────────────────────────────── */}
      {status && (
        <div
          className={`alert ${
            status.type === "success" ? "alert-success" : "alert-danger"
          }`}
        >
          {status.msg}
        </div>
      )}

      <hr />

      {/* ── Patient selector ───────────────────────────────────────── */}
      <div className="card mb-2">
        <div className="card-header primary">
          Choose a Patient to Upload Variant Files For
        </div>
        <div className="card-body">
          <p className="text-muted mb-1" style={{ fontSize: "0.85rem" }}>
            Search by IM number, lab number, or name.
          </p>
          <SearchableSelect
            key={refreshKey}
            value={patientLabel}
            onChange={handlePatientSelect}
            fetchOptions={fetchPatientOptions}
            placeholder="Search patients by IM number, lab number, or name…"
            itemLabel="patients"
          />
        </div>
      </div>

      {/* ── Upload form ────────────────────────────────────────────── */}
      {patientId && (
        <div className="card mb-2">
          <div className="card-header primary">
            Upload Variant File for{" "}
            {selectedPatient?.im_lab_number ??
              selectedPatient?.lab_number ??
              "Patient"}
          </div>
          <div className="card-body">
            <div className="row mb-1">
              <div className="col-2">
                <label className="mb-1">
                  <strong>What are you uploading?</strong>
                </label>
                <div className="flex-gap" style={{ flexWrap: "wrap" }}>
                  {(Object.keys(UPLOAD_LABELS) as UploadType[]).map((t) => (
                    <label key={t} style={{ cursor: "pointer" }}>
                      <input
                        type="radio"
                        name="uploadType"
                        value={t}
                        checked={uploadType === t}
                        onChange={() => {
                          setUploadType(t);
                          if (fileRef.current) fileRef.current.value = "";
                        }}
                      />{" "}
                      {UPLOAD_LABELS[t]}
                    </label>
                  ))}
                </div>
              </div>
              <div className="col-2">
                <label className="mb-1">
                  <strong>Choose file</strong>
                </label>
                <input
                  ref={fileRef}
                  type="file"
                  className="form-control"
                  accept={ACCEPT[uploadType]}
                />
              </div>
            </div>

            <button
              className="btn btn-primary mt-1"
              disabled={uploading}
              onClick={handleUpload}
            >
              {uploading ? "Uploading…" : "Upload"}
            </button>
            <button
              className="btn btn-secondary mt-1 ml-2"
              style={{ marginLeft: "0.5rem" }}
              disabled={!lastUploaded?.labNumber}
              onClick={() => {
                if (!lastUploaded?.labNumber) return;
                const reportType =
                  lastUploaded.testType === "trio" ? "trio" : "singleton";
                const params = new URLSearchParams({
                  lab_number: lastUploaded.labNumber,
                  test_type: reportType,
                });
                navigate(`/report?${params.toString()}`);
              }}
            >
              Generate Report
            </button>

            {/* ── Contextual guidance per file type ── */}
            <div
              className="mt-2"
              style={{
                fontSize: "0.85rem",
                background: "#f8fafc",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                padding: "0.85rem 1rem",
              }}
            >
              {uploadType === "vcf" && (
                <>
                  <strong style={{ display: "block", marginBottom: "0.35rem" }}>
                    Raw Variant Call File
                  </strong>
                  <p className="text-muted" style={{ marginBottom: "0.4rem" }}>
                    Upload a <strong>.vcf</strong>, <strong>.vcf.gz</strong>, or
                    <strong> .bcf</strong> file. The file is stored under the
                    patient-specific data directory and linked to this patient.
                  </p>
                  <p className="text-muted" style={{ marginBottom: "0.4rem" }}>
                    VCF uploads are tracked in the database for audit and can be
                    listed or deleted from this page.
                  </p>
                  <p className="text-muted" style={{ marginBottom: 0 }}>
                    In production, set <code>DATA_DIR</code> to your mounted
                    remote storage (NFS, EFS, SMB, S3-Fuse, etc.) so files are
                    written there instead of local disk.
                  </p>
                </>
              )}

              {uploadType === "singleton" && (
                <>
                  <strong style={{ display: "block", marginBottom: "0.35rem" }}>
                    Singleton Variant Spreadsheet
                  </strong>
                  <p className="text-muted" style={{ marginBottom: "0.4rem" }}>
                    Upload an <strong>.xlsx</strong> file where each row is a
                    single variant finding for this patient. The system
                    auto-detects header rows and fuzzy-maps column names to
                    database fields — spaces and case differences are handled
                    automatically.
                  </p>
                  <p className="text-muted" style={{ marginBottom: "0.4rem" }}>
                    <strong>Recognised columns:</strong>{" "}
                    <code>reportable_variant</code>, <code>chr_pos</code>,{" "}
                    <code>ref_alt</code>, <code>gene_names</code>,{" "}
                    <code>hgvs_c</code>, <code>hgvs_p</code>,{" "}
                    <code>exon_number</code>, <code>zygosity</code>,{" "}
                    <code>inheritance</code>, <code>inherited_from</code>,{" "}
                    <code>classification</code>, <code>omim_id</code>,{" "}
                    <code>rsid</code>, <code>igv_review</code>,{" "}
                    <code>second_review_comment</code>, <code>title</code>,{" "}
                    <code>gene_region_combined</code>.
                  </p>
                  <p className="text-muted" style={{ marginBottom: 0 }}>
                    Unrecognised columns are silently ignored — your spreadsheet
                    can contain extra columns without causing errors.
                  </p>
                </>
              )}

              {uploadType === "trio" && (
                <>
                  <strong style={{ display: "block", marginBottom: "0.35rem" }}>
                    Trio Variant Spreadsheet
                  </strong>
                  <p className="text-muted" style={{ marginBottom: "0.4rem" }}>
                    Upload an <strong>.xlsx</strong> file containing trio
                    analysis variant findings (proband + parents). Each row
                    becomes a Trio variant record linked to the selected
                    patient.
                  </p>
                  <p className="text-muted" style={{ marginBottom: "0.4rem" }}>
                    <strong>Recognised columns:</strong>{" "}
                    <code>reportable_variant</code>, <code>chr_pos</code>,{" "}
                    <code>ref_alt</code>, <code>gene_names</code>,{" "}
                    <code>hgvs_c</code>, <code>hgvs_p</code>,{" "}
                    <code>exon_number</code>, <code>zygosity</code>,{" "}
                    <code>inheritance</code>, <code>inherited_from</code>,{" "}
                    <code>classification</code>, <code>omim_id</code>,{" "}
                    <code>rsid</code>, <code>igv_review</code>,{" "}
                    <code>second_review_comment</code>, <code>title</code>,{" "}
                    <code>gene_region_combined</code>.
                  </p>
                  <p className="text-muted" style={{ marginBottom: 0 }}>
                    Column names are fuzzy-matched — spaces, underscores, and
                    case differences are handled automatically. Extra columns
                    are skipped.
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── VCF files list ─────────────────────────────────────────── */}
      {patientId && vcfFiles.length > 0 && (
        <div className="card mb-2">
          <div className="card-header">
            VCF Files for{" "}
            {selectedPatient?.im_lab_number ?? selectedPatient?.lab_number}
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Size</th>
                  <th>Uploaded</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {vcfFiles.map((v) => (
                  <tr key={v.id}>
                    <td>
                      <code>{v.filename}</code>
                    </td>
                    <td>{formatBytes(v.file_size)}</td>
                    <td>
                      {v.uploaded_at
                        ? new Date(v.uploaded_at).toLocaleString()
                        : "—"}
                    </td>
                    <td>
                      <button
                        className="btn btn-outline-danger btn-sm"
                        onClick={() => handleDeleteVcf(v)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── QC Bulk Upload (no patient required) ───────────────────── */}
      <hr />
      <h3>QC Bulk Upload</h3>
      <p className="text-muted mb-2">
        Upload a wide-format QC file (CSV / TSV) containing many samples.
        The first column after the metric name is the positive control;
        remaining columns are matched against patient lab numbers / IM numbers.
      </p>

      {qcError && (
        <div className="alert alert-danger">{qcError}</div>
      )}

      {qcResult && (
        <div className="alert alert-success">
          <strong>Upload successful</strong>
          <div>Batch: <code>{qcResult.batch ?? "—"}</code></div>
          <div>Type: {qcResult.qc_type}</div>
          <div>Matched: {qcResult.matched_count}</div>
          {qcResult.control_count > 0 && (
            <div>Controls: {qcResult.control_count}</div>
          )}
          {qcResult.unmatched.length > 0 && (
            <div className="text-danger">
              Unmatched labels: {qcResult.unmatched.join(", ")}
            </div>
          )}
        </div>
      )}

      <div className="card mb-2">
        <div className="card-header primary">Upload QC File</div>
        <div className="card-body">
          <div className="row mb-1">
            <div className="col-2">
              <label className="mb-1"><strong>QC Type</strong></label>
              <div className="flex-gap" style={{ flexWrap: "wrap" }}>
                {(["panel", "exome"] as QcType[]).map((t) => (
                  <label key={t} style={{ cursor: "pointer" }}>
                    <input
                      type="radio"
                      name="qcType"
                      value={t}
                      checked={qcType === t}
                      onChange={() => setQcType(t)}
                    />{" "}
                    {t}
                  </label>
                ))}
              </div>
            </div>
            <div className="col-2">
              <label className="mb-1"><strong>Choose file</strong></label>
              <input
                type="file"
                className="form-control"
                accept=".csv,.tsv"
                onChange={(e) => setQcFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>
          <button
            className="btn btn-primary mt-1"
            disabled={qcUploading || !qcFile}
            onClick={handleQcUpload}
          >
            {qcUploading ? "Uploading…" : "Upload QC"}
          </button>
        </div>
      </div>
    </>
  );
}
