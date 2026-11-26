# 1 — System Diagram (components as they exist today)

Rendered by GitHub natively. Status markers: **LIVE** components run in production; dashed boxes are offline/unused right now.

```mermaid
flowchart TB
    subgraph USERS["Users"]
        U1["Job seeker — browser / mobile"]
        U2["Operator (owner) — GitHub Actions / passcode"]
    end

    subgraph SRC["External job sources"]
        S1["Commercial job-board API A (primary volume)"]
        S2["Commercial job-board API B"]
        S3["Open web scraper — major boards (vendor unnamed)"]
        S4["Public ATS feeds — Greenhouse / Lever / Ashby / Workable / SmartRecruiters"]
        S5["Frontier LLM APIs — resume profile / cover letter"]
    end

    subgraph INGEST["Daily collection — sync-jobs-oct26.yml (GitHub Actions)"]
        CNTRL["POST /api/v1/pipeline/finalize (controller.py)"]
        DEDUP["dedup — exact key/URL + AI semantic dedup (cosine ≥ 0.88)"]
        UKFLT["is_uk_location filter (~16% dropped)"]
        RISK["Risk screening — ghost / spam / resume-harvest flags + PII scrub"]
    end

    subgraph IDX["Corpus-first search index — index_store.py"]
        FTS["SQLite FTS5 full-text search (title / company / location / description / skills)"]
        VEC["Vector cosine search — all-mpnet embeddings (BLOB column)"]
        SHARD["Date-partitioned shards corpus_index_YYYY_MM_DD.sqlite3"]
        ENSURE["ensure_fresh() — self-heal: rebuild catalog when corpus newer than served copy"]
    end

    subgraph SPACE["HuggingFace PRO Space — nginx + uvicorn :7860"]
        FE["Frontend React SPA (Vite) — Landing page · sector catalog strip · CV match · results table · source tabs"]
        BE["Backend FastAPI /api/v1 — finalize · cvsearch/stream · trust-score · job-catalog · saved-links · auth / profile / cover-letter · health / system"]
        CACHE["24-h response cache (in-memory + SQLite)"]
    end

    subgraph RAG["RAG trust-score pipeline — trust_score.py"]
        EMB["Job text → embed (all-mpnet)"]
        RET["FTS5 corpus retrieve — top-10 context chunks + vector dupes"]
        CTX["RAG context block (max 10 chunks) + facts"]
        TCHR["Tier-2 teacher LLM — strict JSON verdict: 5 flags + 0–100 score + citations via OpenAI-compatible gateway (~$2, quota-guarded)"]
        FALL["Fallback keyword scorer if teacher unavailable"]
        OUT["Trust badge on job card → trust_labels.jsonl"]
    end

    subgraph TRAIN["AI plane — teacher → student learning loop (~$2.50 total)"]
        T1["Tier 1 — local DistilBERT batch inference — $0; only LOW-CONFIDENCE slice (~10–20%) continues"]
        T2["Tier 2 — teacher LLM verifies uncertain slice (~$2 / full pass)"]
        T3["Tier 3 — student DistilBERT 67M — retrained on Tier-2-verified labels"]
        PROMO["Promotes only if beats teacher agreement on held-out data"]
    end

    subgraph HF["HuggingFace PRO — all repos PRIVATE"]
        D1[("pro-data jobs repo — *_latest.jsonl · deduped_jobs.json · job_type_catalog.json")]
        D2[("dev-autotrain training repo — data/shards/<date>/<hash>.jsonl · train/validation/test.parquet · pairs")]
        D3[("autotrain-models model repo — c1-jobtag-distilbert-v1")]
    end

    subgraph OPS["GitHub Actions"]
        A1["ci.yml — checks + Space deploy"]
        A2["sync-jobs-oct26.yml — daily 06:00 UTC collect + finalize"]
        A3["compact-dataset.yml — nightly 08:00 UTC compact"]
        A4["train-student — manual dispatch only"]
    end

    U1 -->|browse| FE
    U2 -->|trigger| OPS
    S1 & S2 & S3 & S4 -->|daily collect| A2
    CNTRL --> DEDUP --> UKFLT --> RISK
    RISK -->|deduped_jobs.json + *_latest.jsonl| CNTRL
    CNTRL -->|build index| SHARD
    CNTRL -->|upload_file| D1 & D2
    ENSURE -.->|self-heal read path| SHARD
    SHARD --> FTS & VEC
    FTS & VEC -->|warm sub-second answers| BE
    BE -->|fetch catalog JSON| FE
    BE -->|SSE stream| FE
    BE -->|/trust-score RAG| RAG
    EMB --> RET --> CTX
    CTX --> TCHR & FALL
    TCHR --> OUT
    OUT -->|append labels| TRAIN
    T1 --> T2 --> T3 --> PROMO
    T3 -.->|serves at $0| BE
    PROMO -.->|Step C: distill teacher → local model| D3
    A1 -->|deploy code| SPACE
    A3 -->|/dataset/compact| CNTRL
    D2 -.->|dataset mirror commit| OPS

    classDef user fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef source fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef ingest fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef search fill:#f3e5f4,stroke:#7b1fa2,stroke-width:2px
    classDef serve fill:#e0f7fa,stroke:#00838f,stroke-width:2px
    classDef rag fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef ai fill:#f3e5f4,stroke:#7b1fa2,stroke-width:2px
    classDef store fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef ops fill:#fafafa,stroke:#9e9e9e,stroke-width:2px

    class U1,U2 user
    class S1,S2,S3,S4,S5 source
    class CNTRL,DEDUP,UKFLT,RISK ingest
    class FTS,VEC,SHARD,ENSURE search
    class FE,BE,CACHE serve
    class EMB,RET,CTX,TCHR,FALL,OUT rag
    class T1,T2,T3,PROMO ai
    class D1,D2,D3 store
    class A1,A2,A3,A4 ops

    linkStyle default stroke-width:1.5px,fill:none,stroke:#666
    linkStyle 0 stroke:#2e7d32,stroke-width:2px
    linkStyle 1 stroke:#ef6c00,stroke-width:2px
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
