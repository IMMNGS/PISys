import { useEffect, useState, useCallback } from "react";
import {
  fetchCombinedTermOptions,
  fetchHPOTermById,
  fetchDiseaseTermById,
  updateDiseaseTerm,
  deleteDiseaseTerm,
  upsertFreeTextTerm,
  fetchPatientOptions,
  assignTerms,
  removeTerms,
  refreshHPOTerms,
} from "../api/client";
import type { DiseaseTerm } from "../types";
import type { HPOTerm } from "../types";
import SearchableMultiSelect from "../components/SearchableMultiSelect";

type BrowseTerm = {
  id: number;
  term_type: "hpo" | "disease";
  term_id: number;
  hpo_id?: string;
  term_name: string;
  label: string;
};

type DetailTerm =
  | { kind: "hpo"; value: HPOTerm }
  | { kind: "disease"; value: DiseaseTerm };

export default function ManageHpo() {
  // ── Selection state ────────────────────────────────────────────────────
  const [selectedTermIds, setSelectedTermIds] = useState<Set<number>>(
    new Set(),
  );
  const [selectedTermLabels, setSelectedTermLabels] = useState<
    Map<number, string>
  >(new Map());
  const [selectedPatientIds, setSelectedPatientIds] = useState<Set<number>>(
    new Set(),
  );
  const [selectedPatientLabels, setSelectedPatientLabels] = useState<
    Map<number, string>
  >(new Map());

  // ── Messages ───────────────────────────────────────────────────────────
  const [assignMsg, setAssignMsg] = useState<{
    type: string;
    text: string;
  } | null>(null);

  // Browse table state (HPO + disease terms)
  const [browseSearch, setBrowseSearch] = useState("");
  const [browseResults, setBrowseResults] = useState<BrowseTerm[]>([]);
  const [browsePage, setBrowsePage] = useState(1);
  const [browsePages, setBrowsePages] = useState(0);
  const [detailTerm, setDetailTerm] = useState<DetailTerm | null>(null);
  const [editingTermId, setEditingTermId] = useState<number | null>(null);
  const [editTermName, setEditTermName] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editMsg, setEditMsg] = useState<{ type: string; text: string } | null>(
    null,
  );

  // ── Fetch callbacks for SearchableMultiSelect ─────────────────────────
  const fetchTermItems = useCallback(
    async (search: string, limit: number, offset: number) => {
      const result = await fetchCombinedTermOptions(search, limit, offset);
      const items = result.items.map((t) => ({
        id: t.id,
        label: t.label,
      }));
      // Track labels for selected tags
      for (const item of items) {
        setSelectedTermLabels((prev) => new Map(prev).set(item.id, item.label));
      }
      return { items, total: result.total };
    },
    [],
  );

  const fetchPatientItems = useCallback(
    async (search: string, limit: number, offset: number) => {
      const result = await fetchPatientOptions(search, limit, offset);
      const items = result.items.map((p) => ({
        id: p.id,
        label: `${p.im_lab_number ?? p.lab_number} \u2014 ${p.name ?? "N/A"}${p.im_lab_number ? ` (Lab ${p.lab_number})` : ""}`,
      }));
      // Track labels for selected tags
      for (const item of items) {
        setSelectedPatientLabels((prev) =>
          new Map(prev).set(item.id, item.label),
        );
      }
      return { items, total: result.total };
    },
    [],
  );

  // ── Term selection (HPO + free-text) ──────────────────────────────────
  const toggleTerm = (id: number) => {
    setSelectedTermIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const removeTerm = (id: number) => {
    setSelectedTermIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const createFreeTextTerm = useCallback(async (text: string) => {
    const result = await upsertFreeTextTerm(text);
    const item = { id: result.id, label: result.label };
    setSelectedTermLabels((prev) => new Map(prev).set(item.id, item.label));
    return item;
  }, []);

  // ── Patient selection ──────────────────────────────────────────────────
  const togglePatient = (id: number) => {
    setSelectedPatientIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const removePatient = (id: number) => {
    setSelectedPatientIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  // Reset labels when assignment succeeds
  const clearSelections = () => {
    setSelectedTermIds(new Set());
    setSelectedPatientIds(new Set());
    setSelectedTermLabels(new Map());
    setSelectedPatientLabels(new Map());
  };

  // ── Assign action ─────────────────────────────────────────────────────
  const handleAssign = async () => {
    try {
      const result = await assignTerms(
        [...selectedPatientIds],
        [...selectedTermIds],
      );
      setAssignMsg({ type: "success", text: result.message });
      clearSelections();
    } catch {
      setAssignMsg({ type: "danger", text: "Failed to assign terms." });
    }
  };

  const handleRemove = async () => {
    try {
      const result = await removeTerms(
        [...selectedPatientIds],
        [...selectedTermIds],
      );
      setAssignMsg({ type: "success", text: result.message });
    } catch {
      setAssignMsg({ type: "danger", text: "Failed to remove terms." });
    }
  };

  // ── Browse combined-terms table ───────────────────────────────────────
  useEffect(() => {
    const timer = setTimeout(() => {
      const limit = 50;
      const offset = (browsePage - 1) * limit;
      fetchCombinedTermOptions(browseSearch, limit, offset).then((data) => {
        setBrowseResults(data.items as BrowseTerm[]);
        setBrowsePages(Math.max(1, Math.ceil(data.total / limit)));
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [browseSearch, browsePage]);

  const handleViewDetails = async (term: BrowseTerm) => {
    if (term.term_type === "hpo") {
      try {
        const row = await fetchHPOTermById(term.term_id);
        setDetailTerm({ kind: "hpo", value: row });
      } catch {
        setDetailTerm(null);
      }
      return;
    }
    try {
      const row = await fetchDiseaseTermById(term.term_id);
      setDetailTerm({ kind: "disease", value: row });
    } catch {
      setDetailTerm(null);
    }
  };

  const handleStartEdit = (term: DiseaseTerm) => {
    setEditMsg(null);
    setEditingTermId(term.id);
    setEditTermName(term.term_name ?? "");
    setEditNotes(term.notes ?? "");
  };

  const handleSaveEdit = async () => {
    if (!editingTermId) return;
    try {
      await updateDiseaseTerm(editingTermId, {
        term_name: editTermName,
        notes: editNotes,
      });
      setEditMsg({ type: "success", text: "Disease term updated." });
      setEditingTermId(null);
      const limit = 50;
      const offset = (browsePage - 1) * limit;
      const data = await fetchCombinedTermOptions(browseSearch, limit, offset);
      setBrowseResults(data.items as BrowseTerm[]);
      setBrowsePages(Math.max(1, Math.ceil(data.total / limit)));
      if (
        detailTerm?.kind === "disease" &&
        detailTerm.value.id === editingTermId
      ) {
        const refreshed = await fetchDiseaseTermById(editingTermId);
        setDetailTerm({ kind: "disease", value: refreshed });
      }
    } catch (e: unknown) {
      setEditMsg({
        type: "danger",
        text: e instanceof Error ? e.message : "Failed to update disease term.",
      });
    }
  };

  const handleDeleteDiseaseTerm = async (term: BrowseTerm) => {
    if (term.term_type !== "disease") return;
    if (!confirm(`Delete disease term: ${term.term_name}?`)) return;
    try {
      await deleteDiseaseTerm(term.term_id);
      setEditMsg({ type: "success", text: "Disease term deleted." });
      if (
        detailTerm?.kind === "disease" &&
        detailTerm.value.id === term.term_id
      ) {
        setDetailTerm(null);
      }
      if (editingTermId === term.term_id) {
        setEditingTermId(null);
      }
      const limit = 50;
      const offset = (browsePage - 1) * limit;
      const data = await fetchCombinedTermOptions(browseSearch, limit, offset);
      setBrowseResults(data.items as BrowseTerm[]);
      setBrowsePages(Math.max(1, Math.ceil(data.total / limit)));
    } catch (e: unknown) {
      setEditMsg({
        type: "danger",
        text: e instanceof Error ? e.message : "Failed to delete disease term.",
      });
    }
  };

  const handleRefreshHPO = async () => {
    if (
      !window.confirm(
        "This will pull the latest HPO terms into the database. It may take a minute. Continue?",
      )
    )
      return;
    try {
      const res = await refreshHPOTerms();
      alert(
        `Refreshed successfully: ${res.added} added, ${res.updated} updated.`,
      );
      setBrowsePage(1);
    } catch (e: any) {
      alert("Failed to refresh HPO terms: " + (e.message || "Unknown error"));
    }
  };

  const canAssign = selectedTermIds.size > 0 && selectedPatientIds.size > 0;

  return (
    <>
      {/* Header */}
      <div className="flex-between mb-1">
        <h2>Manage Disease Terms</h2>
        <button className="btn btn-sm btn-outline" onClick={handleRefreshHPO}>
          Refresh HPO Terms
        </button>
      </div>
      <p className="text-muted mb-2">
        Use one search to find disease terms, then assign selected terms to
        selected patients.
      </p>

      {/* Side-by-side selectors */}
      <div className="row">
        {/* Disease Terms dropdown */}
        <div className="col-2">
          <div className="card">
            <div className="card-header primary">Disease Terms</div>
            <div className="card-body">
              <SearchableMultiSelect
                selectedIds={selectedTermIds}
                onToggle={toggleTerm}
                fetchOptions={fetchTermItems}
                onCreateFromSearch={createFreeTextTerm}
                createLabelPrefix="Add disease term"
                placeholder="Search disease terms…"
                itemLabel="terms"
              />
              {selectedTermIds.size > 0 && (
                <div className="selected-tags mt-1">
                  <small className="text-muted">Selected:</small>
                  <div className="tag-list">
                    {[...selectedTermIds].map((id) => (
                      <span key={id} className="tag">
                        {selectedTermLabels.get(id) ?? `#${id}`}
                        <button
                          className="tag-remove"
                          onClick={() => removeTerm(id)}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Patients dropdown */}
        <div className="col-2">
          <div className="card">
            <div className="card-header success">Patients</div>
            <div className="card-body">
              <SearchableMultiSelect
                selectedIds={selectedPatientIds}
                onToggle={togglePatient}
                fetchOptions={fetchPatientItems}
                placeholder="Select patients…"
                itemLabel="patients"
              />
              {selectedPatientIds.size > 0 && (
                <div className="selected-tags mt-1">
                  <small className="text-muted">Selected:</small>
                  <div className="tag-list">
                    {[...selectedPatientIds].map((id) => (
                      <span key={id} className="tag">
                        {selectedPatientLabels.get(id) ?? `#${id}`}
                        <button
                          className="tag-remove"
                          onClick={() => removePatient(id)}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="text-center mt-2">
        <button
          className="btn btn-primary btn-lg"
          disabled={!canAssign}
          onClick={handleAssign}
        >
          Assign Selected Terms → Selected Patients ({selectedTermIds.size}{" "}
          terms, {selectedPatientIds.size} patients)
        </button>
        <button
          className="btn btn-outline-danger btn-lg"
          disabled={!canAssign}
          onClick={handleRemove}
          style={{ marginLeft: "0.75rem" }}
        >
          Remove Selected Terms from Selected Patients
        </button>
      </div>

      {assignMsg && (
        <div className={`alert alert-${assignMsg.type} mt-2`}>
          {assignMsg.text}
        </div>
      )}

      <hr />

      {/* Browse combined terms table */}
      <h3>Browse Disease Term</h3>
      <input
        type="text"
        className="form-control mb-2"
        placeholder="Search by disease term, HPO ID, or HPO term name…"
        value={browseSearch}
        onChange={(e) => {
          setBrowseSearch(e.target.value);
          setBrowsePage(1);
        }}
      />

      {editMsg && (
        <div className={`alert alert-${editMsg.type} mb-2`}>{editMsg.text}</div>
      )}

      <div className="table-wrap table-scroll">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Identifier</th>
              <th>Term Name</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {browseResults.length === 0 ? (
              <tr>
                <td colSpan={4} className="text-center text-muted">
                  No results found.
                </td>
              </tr>
            ) : (
              browseResults.map((t) => (
                <tr key={`${t.term_type}-${t.term_id}`}>
                  <td>{t.term_type === "hpo" ? "HPO" : "Disease"}</td>
                  <td>
                    {t.term_type === "hpo"
                      ? (t.hpo_id ?? "—")
                      : `D-${t.term_id}`}
                  </td>
                  <td>{t.term_name}</td>
                  <td>
                    <div className="flex-gap">
                      <button
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => handleViewDetails(t)}
                      >
                        View details
                      </button>
                      {t.term_type === "disease" && (
                        <>
                          <button
                            className="btn btn-outline btn-sm"
                            onClick={() =>
                              handleStartEdit({
                                id: t.term_id,
                                term_name: t.term_name,
                                notes:
                                  detailTerm?.kind === "disease" &&
                                  detailTerm.value.id === t.term_id
                                    ? (detailTerm.value.notes ?? null)
                                    : null,
                              })
                            }
                          >
                            Edit
                          </button>
                          <button
                            className="btn btn-outline-danger btn-sm"
                            onClick={() => handleDeleteDiseaseTerm(t)}
                          >
                            Delete
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {detailTerm && (
        <div className="card mt-2">
          <div className="card-header">Term Details</div>
          <div className="card-body">
            {detailTerm.kind === "hpo" ? (
              <>
                <p>
                  <strong>HPO ID:</strong> {detailTerm.value.hpo_id}
                </p>
                <p>
                  <strong>Term Name:</strong> {detailTerm.value.term_name}
                </p>
                <p>
                  <strong>Definition:</strong>{" "}
                  {detailTerm.value.definition || "—"}
                </p>
                <p>
                  <strong>Synonyms:</strong> {detailTerm.value.synonyms || "—"}
                </p>
              </>
            ) : (
              <>
                <p>
                  <strong>Name:</strong> {detailTerm.value.term_name}
                </p>
                <p>
                  <strong>Identifier:</strong>{" "}
                  {detailTerm.value.normalized_name ?? "—"}
                </p>
                <p>
                  <strong>Notes:</strong> {detailTerm.value.notes || "—"}
                </p>
                <p>
                  <strong>Created:</strong>{" "}
                  {detailTerm.value.created_at
                    ? new Date(detailTerm.value.created_at).toLocaleString()
                    : "—"}
                </p>
              </>
            )}
          </div>
        </div>
      )}

      {editingTermId !== null && (
        <div className="card mt-2">
          <div className="card-header">Edit Free-Text Disease Term</div>
          <div className="card-body">
            <div className="row mb-1">
              <div className="col-2">
                <label className="mb-1">
                  <strong>Term Name</strong>
                </label>
                <input
                  className="form-control"
                  value={editTermName}
                  onChange={(e) => setEditTermName(e.target.value)}
                />
              </div>
              <div className="col-2">
                <label className="mb-1">
                  <strong>Notes</strong>
                </label>
                <input
                  className="form-control"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                />
              </div>
            </div>
            <div className="flex-gap">
              <button className="btn btn-primary" onClick={handleSaveEdit}>
                Save
              </button>
              <button
                className="btn btn-outline-secondary"
                onClick={() => setEditingTermId(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {browsePages > 1 &&
        (() => {
          const maxButtons = 7;
          const half = Math.floor(maxButtons / 2);
          let start = Math.max(1, browsePage - half);
          const end = Math.min(browsePages, start + maxButtons - 1);
          if (end - start + 1 < maxButtons)
            start = Math.max(1, end - maxButtons + 1);
          const pages = Array.from(
            { length: end - start + 1 },
            (_, i) => start + i,
          );
          return (
            <div className="pagination">
              <button
                disabled={browsePage === 1}
                onClick={() => setBrowsePage(1)}
              >
                «
              </button>
              <button
                disabled={browsePage === 1}
                onClick={() => setBrowsePage(browsePage - 1)}
              >
                ‹
              </button>
              {start > 1 && <button disabled>…</button>}
              {pages.map((pg) => (
                <button
                  key={pg}
                  className={pg === browsePage ? "active" : ""}
                  onClick={() => setBrowsePage(pg)}
                >
                  {pg}
                </button>
              ))}
              {end < browsePages && <button disabled>…</button>}
              <button
                disabled={browsePage === browsePages}
                onClick={() => setBrowsePage(browsePage + 1)}
              >
                ›
              </button>
              <button
                disabled={browsePage === browsePages}
                onClick={() => setBrowsePage(browsePages)}
              >
                »
              </button>
              <span
                style={{
                  marginLeft: "0.5rem",
                  fontSize: "0.85rem",
                  color: "var(--muted)",
                  alignSelf: "center",
                }}
              >
                Page {browsePage} of {browsePages}
              </span>
            </div>
          );
        })()}
    </>
  );
}
