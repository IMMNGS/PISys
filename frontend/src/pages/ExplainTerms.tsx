import { useState } from "react";
import { explainEntity, type ExplainResponse } from "../api/client";

type ExplainKind = "hpo" | "variant" | "text";

export default function ExplainTerms() {
  // TODO(model-settings): Add local model settings state/UI (model name,
  // max tokens, temperature) when local runtime integration is added.
  const [kind, setKind] = useState<ExplainKind>("hpo");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExplainResponse | null>(null);

  const handleExplain = async () => {
    // TODO(cache): Check local cache first and reuse previous explanation
    // for identical (kind, query) before calling API.
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await explainEntity(kind, query.trim());
      setResult(response);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Explain request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <h2>Local Explain Helper</h2>
      <p className="text-muted mb-2">
        Explain HPO terms and variants locally. This page is designed for a
        fully local workflow and currently uses local database/rule-based
        explanations.
      </p>

      <div className="card mb-2">
        <div className="card-header primary">Explain Input</div>
        <div className="card-body">
          {/* TODO(ux): Add quick-action explain buttons for selected HPO/variant
              items on patient pages and optionally a floating trigger button. */}
          <div className="flex-gap mb-1" style={{ flexWrap: "wrap" }}>
            <label>
              <input
                type="radio"
                name="kind"
                value="hpo"
                checked={kind === "hpo"}
                onChange={() => setKind("hpo")}
              />{" "}
              HPO term
            </label>
            <label>
              <input
                type="radio"
                name="kind"
                value="variant"
                checked={kind === "variant"}
                onChange={() => setKind("variant")}
              />{" "}
              Variant
            </label>
            <label>
              <input
                type="radio"
                name="kind"
                value="text"
                checked={kind === "text"}
                onChange={() => setKind("text")}
              />{" "}
              Free text
            </label>
          </div>

          <textarea
            className="form-control mb-1"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
            placeholder={
              kind === "hpo"
                ? "e.g. HP:0001250 or Seizure"
                : kind === "variant"
                  ? "e.g. chr2:191092370 C>T in STAT1"
                  : "Type term/variant context..."
            }
          />

          <button
            className="btn btn-primary"
            disabled={loading}
            onClick={handleExplain}
          >
            {loading ? "Explaining…" : "Explain"}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {result && (
        <div className="card">
          <div className="card-header primary">Explanation</div>
          <div className="card-body">
            {/* TODO(citations): Show structured evidence section with matched
                local rows/fields that contributed to this explanation. */}
            <p>
              <strong>Source:</strong> {result.source}
            </p>
            {result.matched && (
              <p>
                <strong>Matched:</strong> {result.matched.term_name} (
                {result.matched.hpo_id})
              </p>
            )}
            <p style={{ whiteSpace: "pre-wrap" }}>{result.explanation}</p>
            {result.details?.synonyms && (
              <p style={{ whiteSpace: "pre-wrap" }}>
                <strong>Synonyms:</strong> {result.details.synonyms}
              </p>
            )}
            {result.medical_disclaimer && (
              <>
                {/* TODO(guardrails): Link to local policy page for PHI-safe usage and retention. */}
                <p className="text-muted">{result.medical_disclaimer}</p>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
