import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchQcBatches, deleteQcBatch } from "../api/client";
import type { NgsQcBatchInfo } from "../types";

function fmtBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function QcOverview() {
  const [batches, setBatches] = useState<NgsQcBatchInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchQcBatches();
      setBatches(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load QC batches");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (batch: NgsQcBatchInfo) => {
    if (!confirm(`Delete QC batch "${batch.original_filename}"?\nThis will also remove all linked per-patient QC records.`)) return;
    try {
      await deleteQcBatch(batch.id);
      setBatches((prev) => prev.filter((b) => b.id !== batch.id));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <>
      <div className="flex-between mb-2">
        <h2>QC Batches</h2>
        <span className="text-muted">
          {batches.length} batch{batches.length !== 1 ? "es" : ""}
        </span>
      </div>

      <p className="text-muted mb-2">
        Every uploaded QC file appears here, even when no patients were matched.
        The positive control data is preserved for audit and review.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}

      {loading ? (
        <p className="text-muted">Loading QC batches…</p>
      ) : batches.length === 0 ? (
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
                        background: b.qc_type === "exome" ? "#ede9fe" : "#dbeafe",
                        color: b.qc_type === "exome" ? "#6d28d9" : "#1d4ed8",
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
                  <td>
                    {b.positive_control_label ? (
                      <span>{b.positive_control_label}</span>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
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
                      onClick={() => handleDelete(b)}
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
  );
}
