import { useEffect, useState, useRef, useCallback } from "react";
import {
  fetchPatients,
  fetchPatientOptions as fetchPatientOptionsApi,
  uploadVcfFile,
  uploadSingletonXlsx,
  uploadTrioXlsx,
  uploadPatientsXlsx,
  fetchVcfFiles,
  deleteVcfFile,
} from "../api/client";
import type { PatientInfo, VcfFileInfo } from "../types";
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
  const patientFileRef = useRef<HTMLInputElement>(null);
  const [patientUploading, setPatientUploading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const reloadPatients = () => fetchPatients("").then(setPatients);

  useEffect(() => {
    reloadPatients();
  }, []);

  // Map of lab_number -> patient id for resolving selection
  const patientIdMap = useRef<Map<string, number>>(new Map());

  const fetchPatientOptions = useCallback(
    async (search: string, limit: number, offset: number) => {
      const result = await fetchPatientOptionsApi(search, limit, offset);
      for (const p of result.items) {
        patientIdMap.current.set(p.lab_number, p.id);
      }
      return {
        items: result.items.map(
          (p) => `${p.lab_number} \u2014 ${p.name ?? "Unnamed"}`,
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
    const labNum = label.split(" \u2014 ")[0];
    const id = patientIdMap.current.get(labNum);
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

  const handlePatientListUpload = async () => {
    if (!patientFileRef.current?.files?.length) return;
    const file = patientFileRef.current.files[0];
    setPatientUploading(true);
    setStatus(null);
    try {
      const r = await uploadPatientsXlsx(file);
      setStatus({ type: "success", msg: r.message });
      await reloadPatients();
      // Force the patient dropdown to refetch fresh data
      setRefreshKey((k) => k + 1);
      setPatientId("");
      setPatientLabel("");
      patientIdMap.current.clear();
      if (patientFileRef.current) patientFileRef.current.value = "";
    } catch (e: unknown) {
      setStatus({
        type: "error",
        msg: e instanceof Error ? e.message : "Patient list upload failed",
      });
    } finally {
      setPatientUploading(false);
    }
  };

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
      } else if (uploadType === "singleton") {
        const r = await uploadSingletonXlsx(patientId, file);
        setStatus({ type: "success", msg: r.message });
      } else {
        const r = await uploadTrioXlsx(patientId, file);
        setStatus({ type: "success", msg: r.message });
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

  return (
    <>
      <h2>Upload &amp; Import</h2>
      <p className="text-muted mb-2">
        Import patients from a spreadsheet and upload variant files.
      </p>

      {/* ── Bulk patient import ────────────────────────────────────── */}
      <div className="card mb-2">
        <div className="card-header primary">
          Import Patients from Excel (.xlsx)
        </div>
        <div className="card-body">
          <p className="text-muted mb-1" style={{ fontSize: "0.85rem" }}>
            Upload an <strong>.xlsx</strong> file with one patient per row.
            Required column: <code>lab_number</code>. Optional columns:{" "}
            <code>im_lab_number</code>, <code>name</code>, <code>sex</code>,{" "}
            <code>age</code>, <code>age_unit</code>, <code>dob</code>,{" "}
            <code>ethnicity</code>, <code>type_of_test</code>, etc. Duplicate
            lab numbers are skipped.
          </p>
          <div className="flex-gap">
            <input
              ref={patientFileRef}
              type="file"
              className="form-control"
              accept=".xlsx"
              style={{ maxWidth: "400px" }}
            />
            <button
              className="btn btn-primary"
              disabled={patientUploading}
              onClick={handlePatientListUpload}
            >
              {patientUploading ? "Importing…" : "Import Patients"}
            </button>
          </div>
        </div>
      </div>

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
        <div className="card-header primary">Choose a Patient to Upload Variant Files For</div>
        <div className="card-body">
          <p className="text-muted mb-1" style={{ fontSize: "0.85rem" }}>
            Search by lab number or name.
          </p>
          <SearchableSelect
            key={refreshKey}
            value={patientLabel}
            onChange={handlePatientSelect}
            fetchOptions={fetchPatientOptions}
            placeholder="Search patients by lab number or name…"
            itemLabel="patients"
          />
        </div>
      </div>

      {/* ── Upload form ────────────────────────────────────────────── */}
      {patientId && (
        <div className="card mb-2">
          <div className="card-header primary">
            Upload Variant File for {selectedPatient?.lab_number ?? "Patient"}
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
                    Upload the patient's <strong>.vcf</strong>,{" "}
                    <strong>.vcf.gz</strong>, or <strong>.bcf</strong> file
                    produced by your variant calling pipeline (e.g. GATK
                    HaplotypeCaller, DeepVariant, Dragen).
                  </p>
                  <p className="text-muted" style={{ marginBottom: "0.4rem" }}>
                    The file is saved on the server under{" "}
                    <code>data/vcf/&lt;lab_number&gt;/</code>. Multiple VCF
                    files per patient are supported — they appear in the table
                    below and can be individually deleted.
                  </p>
                  <p className="text-muted" style={{ marginBottom: 0 }}>
                    For remote storage, set the <code>DATA_DIR</code>{" "}
                    environment variable to a network mount (NFS, SSHFS,
                    S3-Fuse, etc.) so files are written there instead of local
                    disk.
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
                    becomes a Trio variant record linked to the selected patient.
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
            VCF Files for {selectedPatient?.lab_number}
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
    </>
  );
}
