import { useEffect, useState, useCallback } from "react";
import {
  fetchCombinedTermOptions,
  fetchHPOTermById,
  fetchDiseaseTermById,
  fetchDiseaseTerms,
  updateDiseaseTerm,
  deleteDiseaseTerm,
  upsertFreeTextTerm,
  fetchPatientOptions,
  fetchPatient,
  assignTerms,
  removeTerms,
  removePatientDiseaseTerm,
  removeHPO,
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

type AssignedPatientTerm = {
  term_id: number;
  term_type: "hpo" | "disease";
  term_name: string;
  hpo_id?: string;
};

export default function ManageHpo() {
  // ── Patient-first assignment state ─────────────────────────────────────
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(
    null,
  );
  const [selectedPatientLabel, setSelectedPatientLabel] = useState("");
  const [patientOptionLabels, setPatientOptionLabels] = useState<
    Map<number, string>
  >(new Map());
  const [assignedTerms, setAssignedTerms] = useState<AssignedPatientTerm[]>([]);
  const [assignedLoading, setAssignedLoading] = useState(false);
  const [selectedAssignTermIds, setSelectedAssignTermIds] = useState<
    Set<number>
  >(new Set());
  const [selectedAssignTermLabels, setSelectedAssignTermLabels] = useState<
    Map<number, string>
  >(new Map());
  const [showManualDiseasePopup, setShowManualDiseasePopup] = useState(false);
  const [manualDiseaseSearch, setManualDiseaseSearch] = useState("");
  const [manualDiseaseItems, setManualDiseaseItems] = useState<DiseaseTerm[]>(
    [],
  );
  const [manualDiseaseLoading, setManualDiseaseLoading] = useState(false);
  const [manualDiseaseMsg, setManualDiseaseMsg] = useState<{
    type: "success" | "danger";
    text: string;
  } | null>(null);
  const [newManualDiseaseName, setNewManualDiseaseName] = useState("");
  const [newManualDiseaseNotes, setNewManualDiseaseNotes] = useState("");
  const [editingManualDiseaseId, setEditingManualDiseaseId] = useState<
    number | null
  >(null);
  const [editingManualDiseaseName, setEditingManualDiseaseName] = useState("");
  const [editingManualDiseaseNotes, setEditingManualDiseaseNotes] =
    useState("");

  // ── Messages ───────────────────────────────────────────────────────────
  const [patientTermMsg, setPatientTermMsg] = useState<{
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
  const fetchAssignTermItems = useCallback(
    async (search: string, limit: number, offset: number) => {
      const result = await fetchCombinedTermOptions(search, limit, offset);
      const items = result.items.map((t) => ({
        id: t.id,
        label: t.label,
      }));
      for (const item of items) {
        setSelectedAssignTermLabels((prev) =>
          new Map(prev).set(item.id, item.label),
        );
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
      for (const item of items) {
        setPatientOptionLabels((prev) =>
          new Map(prev).set(item.id, item.label),
        );
      }
      return { items, total: result.total };
    },
    [],
  );

  const toggleAssignTerm = (id: number) => {
    setSelectedAssignTermIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const removeAssignTerm = (id: number) => {
    setSelectedAssignTermIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const createFreeTextDiseaseTerm = useCallback(async (text: string) => {
    const result = await upsertFreeTextTerm(text);
    const item = { id: result.id, label: result.label };
    setSelectedAssignTermLabels((prev) =>
      new Map(prev).set(item.id, item.label),
    );
    return item;
  }, []);

  const loadManualDiseaseTerms = useCallback(async (searchText: string) => {
    setManualDiseaseLoading(true);
    try {
      const data = await fetchDiseaseTerms(searchText, 1, 100);
      setManualDiseaseItems(data.items);
    } catch {
      setManualDiseaseMsg({
        type: "danger",
        text: "Failed to load manual disease terms.",
      });
    } finally {
      setManualDiseaseLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!showManualDiseasePopup) return;
    const timer = setTimeout(() => {
      void loadManualDiseaseTerms(manualDiseaseSearch);
    }, 250);
    return () => clearTimeout(timer);
  }, [showManualDiseasePopup, manualDiseaseSearch, loadManualDiseaseTerms]);

  const toggleSelectedPatient = (id: number) => {
    setSelectedPatientId((prev) => {
      const next = prev === id ? null : id;
      setSelectedPatientLabel(
        next ? (patientOptionLabels.get(next) ?? "") : "",
      );
      return next;
    });
  };

  const refreshAssignedTerms = useCallback(async (patientId: number) => {
    setAssignedLoading(true);
    try {
      const patient = await fetchPatient(patientId);
      const hpoTerms: AssignedPatientTerm[] = (patient.hpo_terms ?? []).map(
        (term) => ({
          term_id: term.id,
          term_type: "hpo",
          term_name: term.term_name,
          hpo_id: term.hpo_id,
        }),
      );
      const diseaseTerms: AssignedPatientTerm[] = (
        patient.disease_terms ?? []
      ).map((term) => ({
        term_id: -term.id,
        term_type: "disease",
        term_name: term.term_name,
      }));
      setAssignedTerms([...hpoTerms, ...diseaseTerms]);
    } finally {
      setAssignedLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedPatientId) {
      setAssignedTerms([]);
      return;
    }
    void refreshAssignedTerms(selectedPatientId);
  }, [selectedPatientId, refreshAssignedTerms]);

  useEffect(() => {
    if (!selectedPatientId) {
      if (selectedPatientLabel) setSelectedPatientLabel("");
      return;
    }
    const label = patientOptionLabels.get(selectedPatientId);
    if (label && label !== selectedPatientLabel) {
      setSelectedPatientLabel(label);
    }
  }, [selectedPatientId, patientOptionLabels, selectedPatientLabel]);

  const handleAssignTerms = async () => {
    if (!selectedPatientId || selectedAssignTermIds.size === 0) return;
    try {
      const result = await assignTerms(
        [selectedPatientId],
        [...selectedAssignTermIds],
      );
      setPatientTermMsg({ type: "success", text: result.message });
      setSelectedAssignTermIds(new Set());
      await refreshAssignedTerms(selectedPatientId);
    } catch {
      setPatientTermMsg({
        type: "danger",
        text: "Failed to assign terms.",
      });
    }
  };

  const handleAddManualDiseaseTerm = async () => {
    const termName = newManualDiseaseName.trim();
    if (!termName) return;
    try {
      const created = await upsertFreeTextTerm(
        termName,
        newManualDiseaseNotes.trim(),
      );
      setManualDiseaseMsg({
        type: "success",
        text: "Manual disease term saved.",
      });
      setNewManualDiseaseName("");
      setNewManualDiseaseNotes("");
      setSelectedAssignTermLabels((prev) =>
        new Map(prev).set(created.id, created.label),
      );
      await loadManualDiseaseTerms(manualDiseaseSearch);
    } catch {
      setManualDiseaseMsg({
        type: "danger",
        text: "Failed to save manual disease term.",
      });
    }
  };

  const handleDeleteManualDiseaseTerm = async (term: DiseaseTerm) => {
    if (!window.confirm(`Delete manual disease term: ${term.term_name}?`))
      return;
    try {
      await deleteDiseaseTerm(term.id);
      setManualDiseaseMsg({
        type: "success",
        text: "Manual disease term deleted.",
      });
      setSelectedAssignTermIds((prev) => {
        const next = new Set(prev);
        next.delete(-term.id);
        return next;
      });
      if (selectedPatientId) {
        await refreshAssignedTerms(selectedPatientId);
      }
      await loadManualDiseaseTerms(manualDiseaseSearch);
    } catch {
      setManualDiseaseMsg({
        type: "danger",
        text: "Failed to delete manual disease term.",
      });
    }
  };

  const handleStartEditManualDiseaseTerm = (term: DiseaseTerm) => {
    setEditingManualDiseaseId(term.id);
    setEditingManualDiseaseName(term.term_name ?? "");
    setEditingManualDiseaseNotes(term.notes ?? "");
  };

  const handleSaveEditManualDiseaseTerm = async () => {
    if (!editingManualDiseaseId || !editingManualDiseaseName.trim()) return;
    try {
      await updateDiseaseTerm(editingManualDiseaseId, {
        term_name: editingManualDiseaseName.trim(),
        notes: editingManualDiseaseNotes.trim(),
      });
      setManualDiseaseMsg({
        type: "success",
        text: "Manual disease term updated.",
      });
      setEditingManualDiseaseId(null);
      setEditingManualDiseaseName("");
      setEditingManualDiseaseNotes("");
      await loadManualDiseaseTerms(manualDiseaseSearch);
    } catch {
      setManualDiseaseMsg({
        type: "danger",
        text: "Failed to update manual disease term.",
      });
    }
  };

  const handleRemoveSingleAssignedTerm = async (term: AssignedPatientTerm) => {
    if (!selectedPatientId) return;
    try {
      const result =
        term.term_type === "hpo"
          ? await removeHPO(selectedPatientId, term.term_id)
          : await removePatientDiseaseTerm(
              selectedPatientId,
              Math.abs(term.term_id),
            );
      setPatientTermMsg({ type: "success", text: result.message });
      await refreshAssignedTerms(selectedPatientId);
    } catch {
      setPatientTermMsg({ type: "danger", text: "Failed to remove term." });
    }
  };

  const handleRemoveAllAssignedTerms = async () => {
    if (!selectedPatientId || assignedTerms.length === 0) return;
    if (
      !window.confirm(
        "Remove all assigned HPO and disease terms from this patient?",
      )
    )
      return;
    try {
      const result = await removeTerms(
        [selectedPatientId],
        assignedTerms.map((t) => t.term_id),
      );
      setPatientTermMsg({ type: "success", text: result.message });
      await refreshAssignedTerms(selectedPatientId);
    } catch {
      setPatientTermMsg({
        type: "danger",
        text: "Failed to remove all terms.",
      });
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

  const canAssignTerms =
    selectedPatientId !== null && selectedAssignTermIds.size > 0;
  const selectedPatientSet = selectedPatientId
    ? new Set<number>([selectedPatientId])
    : new Set<number>();

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
        Select one patient, review assigned HPO/disease terms, remove one or
        all, then assign HPO or disease terms.
      </p>

      {/* Patient-first disease-term management */}
      <div className="row">
        <div className="col-2">
          <div className="card">
            <div className="card-header success">1. Select Patient</div>
            <div className="card-body">
              <SearchableMultiSelect
                selectedIds={selectedPatientSet}
                onToggle={toggleSelectedPatient}
                fetchOptions={fetchPatientItems}
                placeholder="Search/select one patient…"
                itemLabel="patients"
              />
              {selectedPatientId && (
                <div className="selected-tags mt-1">
                  <small className="text-muted">Current patient:</small>
                  <div className="tag-list">
                    <span className="tag">
                      {selectedPatientLabel || `#${selectedPatientId}`}
                      <button
                        className="tag-remove"
                        onClick={() => setSelectedPatientId(null)}
                      >
                        ×
                      </button>
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-2">
          <div className="card">
            <div className="card-header flex-between">
              <span>2. Assigned Terms</span>
              <button
                className="btn btn-outline-danger btn-sm"
                type="button"
                disabled={!selectedPatientId || assignedTerms.length === 0}
                onClick={handleRemoveAllAssignedTerms}
              >
                Remove all
              </button>
            </div>
            <div className="card-body">
              {!selectedPatientId && (
                <p className="text-muted mb-0">
                  Select a patient to view assigned terms.
                </p>
              )}
              {selectedPatientId && assignedLoading && (
                <p>Loading assigned terms...</p>
              )}
              {selectedPatientId &&
                !assignedLoading &&
                assignedTerms.length === 0 && (
                  <p className="text-muted mb-0">
                    No HPO/disease terms assigned.
                  </p>
                )}
              {selectedPatientId &&
                !assignedLoading &&
                assignedTerms.length > 0 && (
                  <div className="tag-list">
                    {assignedTerms.map((term) => (
                      <span
                        key={`${term.term_type}-${term.term_id}`}
                        className="tag"
                      >
                        {term.term_type === "hpo"
                          ? `[HPO ${term.hpo_id ?? `#${term.term_id}`}] ${term.term_name}`
                          : `[Disease] ${term.term_name}`}
                        <button
                          className="tag-remove"
                          onClick={() => handleRemoveSingleAssignedTerm(term)}
                          title="Remove this term"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
            </div>
          </div>
        </div>

        <div className="col-2">
          <div className="card">
            <div className="card-header primary flex-between">
              <span>3. Assign Terms</span>
              <button
                className="btn btn-sm btn-outline-light"
                type="button"
                onClick={() => {
                  setManualDiseaseMsg(null);
                  setShowManualDiseasePopup(true);
                }}
              >
                Manage Manual Terms
              </button>
            </div>
            <div className="card-body">
              <SearchableMultiSelect
                selectedIds={selectedAssignTermIds}
                onToggle={toggleAssignTerm}
                fetchOptions={fetchAssignTermItems}
                onCreateFromSearch={createFreeTextDiseaseTerm}
                createLabelPrefix="Add disease term"
                placeholder="Search HPO or disease terms..."
                itemLabel="terms"
              />
              {selectedAssignTermIds.size > 0 && (
                <div className="selected-tags mt-1">
                  <small className="text-muted">Ready to assign:</small>
                  <div className="tag-list">
                    {[...selectedAssignTermIds].map((id) => (
                      <span key={id} className="tag">
                        {selectedAssignTermLabels.get(id) ?? `#${id}`}
                        <button
                          className="tag-remove"
                          onClick={() => removeAssignTerm(id)}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="mt-1">
                <button
                  className="btn btn-primary"
                  type="button"
                  disabled={!canAssignTerms}
                  onClick={handleAssignTerms}
                >
                  Assign to selected patient
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {showManualDiseasePopup && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.45)",
            zIndex: 10000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
          onClick={() => setShowManualDiseasePopup(false)}
        >
          <div
            className="card"
            style={{
              width: "min(760px, 96vw)",
              maxHeight: "85vh",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="card-header flex-between">
              <span>Manual Disease Terms</span>
              <button
                className="btn btn-sm btn-outline-secondary"
                type="button"
                onClick={() => setShowManualDiseasePopup(false)}
              >
                Close
              </button>
            </div>
            <div className="card-body">
              {manualDiseaseMsg && (
                <div className={`alert alert-${manualDiseaseMsg.type} mb-1`}>
                  {manualDiseaseMsg.text}
                </div>
              )}

              <div className="row mb-1">
                <div className="col-2">
                  <label className="mb-1">
                    <strong>Add manual disease term</strong>
                  </label>
                  <div className="flex-gap" style={{ flexWrap: "wrap" }}>
                    <input
                      className="form-control"
                      value={newManualDiseaseName}
                      onChange={(e) => setNewManualDiseaseName(e.target.value)}
                      placeholder="Term name"
                    />
                    <textarea
                      className="form-control"
                      value={newManualDiseaseNotes}
                      onChange={(e) => setNewManualDiseaseNotes(e.target.value)}
                      placeholder="Description / notes"
                      rows={3}
                    />
                    <button
                      className="btn btn-primary"
                      type="button"
                      disabled={!newManualDiseaseName.trim()}
                      onClick={handleAddManualDiseaseTerm}
                    >
                      Add
                    </button>
                  </div>
                </div>
              </div>

              <label className="mb-1">
                <strong>Existing manual disease terms</strong>
              </label>
              <input
                className="form-control mb-1"
                value={manualDiseaseSearch}
                onChange={(e) => setManualDiseaseSearch(e.target.value)}
                placeholder="Search manual disease terms..."
              />

              {manualDiseaseLoading ? (
                <p>Loading terms...</p>
              ) : manualDiseaseItems.length === 0 ? (
                <p className="text-muted mb-0">
                  No manual disease terms found.
                </p>
              ) : (
                <div className="table-wrap manual-disease-table-wrap">
                  <table className="manual-disease-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Description / Notes</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {manualDiseaseItems.map((term) => {
                        const isEditing = editingManualDiseaseId === term.id;
                        return (
                          <tr key={term.id}>
                            <td>
                              {isEditing ? (
                                <input
                                  className="form-control"
                                  value={editingManualDiseaseName}
                                  onChange={(e) =>
                                    setEditingManualDiseaseName(e.target.value)
                                  }
                                />
                              ) : (
                                term.term_name
                              )}
                            </td>
                            <td>
                              {isEditing ? (
                                <textarea
                                  className="form-control"
                                  rows={2}
                                  value={editingManualDiseaseNotes}
                                  onChange={(e) =>
                                    setEditingManualDiseaseNotes(e.target.value)
                                  }
                                />
                              ) : (
                                term.notes || "-"
                              )}
                            </td>
                            <td>
                              <div className="flex-gap">
                                {isEditing ? (
                                  <>
                                    <button
                                      className="btn btn-sm btn-primary"
                                      type="button"
                                      disabled={
                                        !editingManualDiseaseName.trim()
                                      }
                                      onClick={handleSaveEditManualDiseaseTerm}
                                    >
                                      Save
                                    </button>
                                    <button
                                      className="btn btn-sm btn-outline-secondary"
                                      type="button"
                                      onClick={() => {
                                        setEditingManualDiseaseId(null);
                                        setEditingManualDiseaseName("");
                                        setEditingManualDiseaseNotes("");
                                      }}
                                    >
                                      Cancel
                                    </button>
                                  </>
                                ) : (
                                  <>
                                    <button
                                      className="btn btn-sm btn-outline"
                                      type="button"
                                      onClick={() =>
                                        handleStartEditManualDiseaseTerm(term)
                                      }
                                    >
                                      Edit
                                    </button>
                                    <button
                                      className="btn btn-sm btn-outline-danger"
                                      type="button"
                                      onClick={() =>
                                        handleDeleteManualDiseaseTerm(term)
                                      }
                                    >
                                      Delete
                                    </button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {patientTermMsg && (
        <div className={`alert alert-${patientTermMsg.type} mt-2`}>
          {patientTermMsg.text}
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
