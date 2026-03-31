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
- [x] Add actual chart visualizations (demographic + VCF summaries now chart-based)
- [x] Add date-range and test-type filters for drill-down analytics
- [x] Add export (CSV/JSON) for stats results

## 2) Local Explain Helper (Small-Model Ready)

- [x] Create backend local explain endpoint: `/api/insights/explain`
- [x] Add local HPO explanation using local DB fields (`definition`, `synonyms`)
- [x] Add local rule-based variant explanation stub
- [x] Create local LLM chat page: `frontend/src/pages/LocalLlm.tsx`
- [x] Add backend chat proxy: `/api/local-llm/chat`
- [x] Add local model listing endpoint: `/api/local-llm/models`
- [x] Add local startup helper for llama.cpp / mock fallback: `scripts/start_local_llm.py`
- [x] Add model settings controls (model name, max tokens, temperature)
- [x] Persist assistant chat history locally in the browser
- [x] Integrate local small-model runtime (llama.cpp loopback server)
- [x] Add response caching (MySQL-backed local table) to reduce repeated inference
- [x] Add PHI-safe logging controls and retention policy
- [x] Add citation mode (show matched HPO rows / variant fields used)

## 3) Validation and Documentation

- [ ] Add backend tests for `/api/insights/summary`
- [ ] Add backend tests for `/api/insights/explain`
- [ ] Add frontend tests for both new pages
- [x] Document local-only deployment in README (`no external API calls`)

## 4) Model Accuracy Improvements (RAG / Fine-tuning)

- [x] Define the local RAG corpus schema and folder layout under `data/rag/`
- [x] Add scripts to download public research sources for offline use
- [ ] Define evaluation set for assistant accuracy using real local cases
- [ ] Add answer-quality metrics for retrieval precision and citation coverage
- [x] Build retrieval layer over local knowledge sources (HPO, disease terms, reports, variant notes)
- [x] Add chunking + embedding pipeline for RAG indexing of local documents
- [ ] Add reranking / source selection before prompt assembly
- [x] Surface citations in the UI for every model answer
- [ ] Add prompt templates that force evidence-based answers and uncertainty handling
- [ ] Create feedback capture for clinician/user corrections on answers
- [ ] Prepare supervised fine-tuning dataset from approved local examples
- [ ] Add a lightweight fine-tuning workflow for the local model when enough labeled data exists
- [ ] Compare baseline vs RAG vs fine-tuned performance on the evaluation set

## 5) Authentication

- [ ] Add user login flow and session handling

## 6) Backups and Restore

- [ ] Define backup scope for MySQL, uploaded files, and config files
- [ ] Add daily automated database backups with retention
- [ ] Add file-system backups for `DATA_DIR` with retention
- [ ] Add encrypted offsite backup copy
- [ ] Add point-in-time recovery using MySQL binlogs
- [ ] Add restore verification script for staging environment
- [ ] Add periodic backup/restore test checklist
- [ ] Document backup, restore, and retention procedures in README

## Notes

- Current local LLM support uses a loopback OpenAI-compatible server and stays on-device.
- `scripts/start_local_llm.py` can launch llama.cpp when available, or fall back to a mock server for UI testing.
- The chat UI reads `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, and the selected GGUF file from the local configuration.
- Current implementation is fully local-only and does not call external LLM APIs.
- The explain endpoint is intentionally lightweight and safe as a first step.
