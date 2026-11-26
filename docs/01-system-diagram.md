# 1 — System Diagram (components as they exist today)

Rendered by GitHub natively. Status markers: **LIVE** components run in production; dashed boxes are offline/unused right now.
# 1 — High-Level System Story (what we do, how it runs, how we keep data safe)

This is the plain-English version of the UK AI Job Hunter. It answers: what we want to do, what the system does, how the AI (RAG) works, how the AI learns, and how privacy is protected. No private service details needed — just the big picture.

```mermaid
flowchart LR
    U[Job seeker] --> W[Web app UI<br/>landing · search · results with trust badges]
    W --> B[Backend service<br/>collect · search · trust score · learn]
    B --> P[Private storage<br/>Hugging Face repos (jobs · training · models)]
    B --> A[AI brain<br/>cheap model first → teacher LLM → student distills]
    A --> W
    B --> S[Job sources<br/>APIs · web scraper · ATS feeds]
```

## Flows — how the work actually moves

| # | Flow | What happens |
|---|---|---|
| **F1** | Daily collection (06:00 UTC) | GitHub Actions triggers the backend to pull ~2,000–3,000 raw postings from commercial APIs, the open scraper, and public ATS feeds (Greenhouse/Lever/Ashby/Workable/SmartRecruiters). |
| **F2** | Dedupe & screen | Exact key/URL dedupe, then AI semantic dedupe (cosine ≥ 0.88). UK-only filter removes ~16%. Ghost/spam/harvest risk scoring runs; PII scrub (emails/phones → `[email]`/`[phone]`) happens before anything is stored. |
| **F3** | Index build | `deduped_jobs.json` → per-day SQLite shard (FTS5 full-text + all-mpnet vector embeddings). Warm searches answer in sub-seconds instead of a 5–15 s live re-scrape. |
| **F4** | Catalog publish | `job_catalog.build_catalog()` buckets jobs into 12 sectors; `job_type_catalog.json` uploads to the private `pro-data` HF repo. `ensure_fresh()` self-heals if a catalog upload ever fails silently (read path rebuilds from the local corpus). |
| **F5** | Frontend serve | The React SPA reads the exported JSONL files directly (no per-click scraping): landing sector strip with 3-day/7-day deltas, CV-driven matches, results table with trust badges. A 24-h cache avoids re-scraping on repeated queries. |
| **F6** | RAG trust score | For each listing: embed text → retrieve top-10 comparable real jobs from FTS5 + vector dupes → assemble a RAG context block → one structured call to the Tier-2 teacher LLM via an OpenAI-compatible gateway → strict-JSON verdict (5 flags + 0–100 score + cited evidence). Falls back to a cheap keyword scorer if the teacher is down. Verdict lands as a trust badge on the job card. |
| **F7** | Teacher → student | Tier-1 local DistilBERT labels everything for $0; Tier-2 teacher reviews only the low-confidence slice (~10–20%, ~$2 total); Tier-3 student DistilBERT retrains on verified labels and promotes itself only when it beats the teacher on held-out data. Total to a self-improving system: ~$2.50. |


## Component inventory

| Layer | Components | Source of truth |
|---|---|---|
| Frontend | Landing page, JobTypeCatalogStrip, My CV Match, Results view, Source tabs | `app/src/` |
| Routers | 13 FastAPI routers under `/api/v1` | `backend/app/routers/` |
| Services | dedup, index_store, semantic_match, matching, training_data, job_catalog, trust_score, dataset_sync, exports, cache, saved_job_links | `backend/app/services/` |
| Core services | SVC — dedup, UK filter, risk screening, index store, vector search, semantic match, LLM pool, training data, job catalog, trust score, dataset sync, exports, cache, saved job links | `backend/app/services/` |
| Storage | 3 private HF repos (pro-data jobs, dev-autotrain training, autotrain-models models) + ephemeral Space disk | `backend/app/core/config.py` |
| Automation | ci.yml, sync-jobs-oct26.yml, compact-dataset.yml, train-student | `.github/workflows/` |
