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
        <div className="card-header primary">1. Select Patient</div>
        <div className="card-body">
          <SearchableSelect
            key={refreshKey}
            value={patientLabel}
            onChange={handlePatientSelect}
            fetchOptions={fetchPatientOptions}
            placeholder="Select patient…"
            itemLabel="patients"
          />
        </div>
      </div>

      {/* ── Upload form ────────────────────────────────────────────── */}
      {patientId && (
        <div className="card mb-2">
          <div className="card-header primary">2. Upload File</div>
          <div className="card-body">
            <div className="row mb-1">
              <div className="col-2">
                <label className="mb-1">
                  <strong>File type</strong>
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

            {uploadType === "vcf" && (
              <p className="text-muted mt-1" style={{ fontSize: "0.85rem" }}>
                VCF files are stored on the server filesystem under{" "}
                <code>data/vcf/&lt;lab_number&gt;/</code>. To store on a remote
                server, set the <code>DATA_DIR</code> environment variable to a
                network mount (NFS, SSHFS, S3-Fuse, etc.).
              </p>
            )}

            {uploadType !== "vcf" && (
              <p className="text-muted mt-1" style={{ fontSize: "0.85rem" }}>
                The XLSX columns should match the database field names
                (case-insensitive, spaces converted to underscores).
                Unrecognised columns are silently ignored.
              </p>
            )}
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
