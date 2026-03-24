# Local-First Feature TODOs

This file tracks the implementation plan for local analytics and local explanation features.

## 1) Descriptive Statistics + Visualization

- [x] Create backend local analytics endpoint: `/api/insights/summary`
- [x] Return counts: patients, singleton/trio/total variants, VCF files
- [x] Return chromosome distribution from variant records
- [x] Return top genes from singleton/trio `gene_names`
- [x] Return top variant frequency list (`chr_pos` + `ref_alt`)
- [x] Return keyword frequency list from local annotation text
- [x] Create frontend page: `frontend/src/pages/DescriptiveStats.tsx`
- [x] Add route + navbar entry for descriptive statistics
- [ ] Add actual chart visualizations (currently table-based)
- [ ] Add date-range and test-type filters for drill-down analytics
- [ ] Add export (CSV/JSON) for stats results

## 2) Local Explain Helper (Small-Model Ready)

- [x] Create backend local explain endpoint: `/api/insights/explain`
- [x] Add local HPO explanation using local DB fields (`definition`, `synonyms`)
- [x] Add local rule-based variant explanation stub
- [x] Create frontend page: `frontend/src/pages/ExplainTerms.tsx`
- [x] Add route + navbar entry for explain helper
- [x] Create local LLM chat page: `frontend/src/pages/LocalLlm.tsx`
- [x] Add backend chat proxy: `/api/local-llm/chat`
- [x] Add model settings controls (model name, max tokens, temperature)
- [ ] Integrate local small-model runtime (optional): Ollama / llama.cpp / vLLM local
- [ ] Add response caching (SQLite/local table) to reduce repeated inference
- [ ] Add PHI-safe logging controls and retention policy
- [ ] Add citation mode (show matched HPO rows / variant fields used)

## 3) Validation and Documentation

- [ ] Add backend tests for `/api/insights/summary`
- [ ] Add backend tests for `/api/insights/explain`
- [ ] Add frontend tests for both new pages
- [ ] Document local-only deployment in README (`no external API calls`)

## Notes

- Current implementation is fully local-only and does not call external LLM APIs.
- The explain endpoint is intentionally lightweight and safe as a first step.
