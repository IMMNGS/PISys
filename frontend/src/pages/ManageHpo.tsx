import { useEffect, useState, useCallback } from "react";
import {
  fetchHPOTerms,
  fetchCombinedTermOptions,
  upsertFreeTextTerm,
  fetchPatientOptions,
  assignTerms,
  refreshHPOTerms,
} from "../api/client";
import type { HPOTerm } from "../types";
import SearchableMultiSelect from "../components/SearchableMultiSelect";

export default function ManageHpo() {
  // ── Selection state ────────────────────────────────────────────────────
  const [selectedTermIds, setSelectedTermIds] = useState<Set<number>>(new Set());
  const [selectedTermLabels, setSelectedTermLabels] = useState<Map<number, string>>(new Map());
  const [selectedPatientIds, setSelectedPatientIds] = useState<Set<number>>(
    new Set(),
  );
  const [selectedPatientLabels, setSelectedPatientLabels] = useState<Map<number, string>>(new Map());

  // ── Messages ───────────────────────────────────────────────────────────
  const [assignMsg, setAssignMsg] = useState<{
    type: string;
    text: string;
  } | null>(null);
  const [refreshMsg, setRefreshMsg] = useState<{
    type: string;
    text: string;
  } | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Browse table state
  const [browseSearch, setBrowseSearch] = useState("");
  const [browseResults, setBrowseResults] = useState<HPOTerm[]>([]);
  const [browsePage, setBrowsePage] = useState(1);
  const [browsePages, setBrowsePages] = useState(0);

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
        label: `${p.lab_number} \u2014 ${p.name ?? "N/A"}`,
      }));
      // Track labels for selected tags
      for (const item of items) {
        setSelectedPatientLabels((prev) => new Map(prev).set(item.id, item.label));
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

  // ── Refresh action ────────────────────────────────────────────────────
  const handleRefresh = async () => {
    setRefreshing(true);
    setRefreshMsg({
      type: "info",
      text: "Pulling latest HPO terms from pyhpo — this may take a minute…",
    });
    try {
      const data = await refreshHPOTerms();
      if (data.error) {
        setRefreshMsg({ type: "danger", text: data.error });
      } else {
        setRefreshMsg({ type: "success", text: data.message });
      }
    } catch {
      setRefreshMsg({ type: "danger", text: "Failed to refresh HPO terms." });
    } finally {
      setRefreshing(false);
    }
  };

  // ── Browse HPO table ──────────────────────────────────────────────────
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchHPOTerms(browseSearch, browsePage, 50).then((data) => {
        setBrowseResults(data.items);
        setBrowsePages(data.pages);
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [browseSearch, browsePage]);

  const canAssign = selectedTermIds.size > 0 && selectedPatientIds.size > 0;

  return (
    <>
      {/* Header */}
      <div className="flex-between mb-1">
        <h2>Manage Disease Terms</h2>
        <button
          className="btn btn-outline-warning"
          disabled={refreshing}
          onClick={handleRefresh}
        >
          {refreshing ? "Refreshing…" : "⟳ Refresh HPO Terms"}
        </button>
      </div>
      <p className="text-muted mb-2">
        Use one search to find disease terms,
        then assign selected terms to selected patients.
      </p>

      {refreshMsg && (
        <div className={`alert alert-${refreshMsg.type}`}>
          {refreshMsg.text}
        </div>
      )}

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
          Assign Selected Terms → Selected Patients ({selectedTermIds.size} terms,
          {" "}{selectedPatientIds.size} patients)
        </button>
      </div>

      {assignMsg && (
        <div className={`alert alert-${assignMsg.type} mt-2`}>
          {assignMsg.text}
        </div>
      )}

      <hr />

      {/* Browse HPO table */}
      <h3>Browse HPO Reference Terms</h3>
      <input
        type="text"
        className="form-control mb-2"
        placeholder="Search by HPO ID, term name, or synonyms…"
        value={browseSearch}
        onChange={(e) => {
          setBrowseSearch(e.target.value);
          setBrowsePage(1);
        }}
      />

      <div className="table-wrap table-scroll">
        <table>
          <thead>
            <tr>
              <th>HPO ID</th>
              <th>Term Name</th>
              <th>Definition</th>
              <th>Synonyms</th>
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
                <tr key={t.id}>
                  <td>
                    <code>{t.hpo_id}</code>
                  </td>
                  <td>{t.term_name}</td>
                  <td>
                    <small>
                      {t.definition
                        ? t.definition.length > 120
                          ? t.definition.slice(0, 120) + "…"
                          : t.definition
                        : "—"}
                    </small>
                  </td>
                  <td>
                    <small>
                      {t.synonyms
                        ? t.synonyms.length > 80
                          ? t.synonyms.slice(0, 80) + "…"
                          : t.synonyms
                        : "—"}
                    </small>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {browsePages > 1 &&
        (() => {
          const maxButtons = 7;
          const half = Math.floor(maxButtons / 2);
          let start = Math.max(1, browsePage - half);
          let end = Math.min(browsePages, start + maxButtons - 1);
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
