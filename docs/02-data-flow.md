# 2 — Data Flow (how every byte moves through the system)

Five flows, numbered in execution order. Numbers show the measured volumes from the 2026-11-17 stocktake.

```mermaid
flowchart TD
    %% ===================== FLOW 1: DAILY COLLECTION (HOT PATH) =====================
    subgraph F1["FLOW 1 — Daily collection · 06:00 UTC · sync-jobs-oct26.yml"]
        direction TB
        S1["Adzuna API<br/>Reed API"] -->|"auth keys"| CO
        S2["JobSpy scraper<br/>Indeed etc."] -->|"scrape"| CO
        S3["Greenhouse · Lever<br/>Ashby · Workable · Arbeitnow"] -->|"ATS boards"| CO
        CO["controller.collect()<br/>~2,000-3,000 raw/day"] -->|"exact + vector dedup<br/>cosine ≥ 0.88"| DD["dedup.deduplicate()<br/>12,780 unique"]
        DD -->|"is_uk_location UK filter"| UK["10,728 UK jobs"]
        UK -->|"ghost / spam score"| GATE["quality gate"]
        GATE -->|"deduped_jobs.json (19.5 MB)"| EXPORT["exports/"]
        GATE -->|"*_latest.jsonl<br/>adzuna 9,776 · jobspy 225"| EXPORT
        EXPORT -->|"jobs_history.jsonl<br/>git commit 4ffe8b6"| GIT["GitHub main"]
        EXPORT -->|"upload_file"| HFD1[("HF pro-data<br/>11 canonical files")]
    end

    %% ===================== FLOW 2: TRAINING DATA (COLD PATH) =====================
    subgraph F2["FLOW 2 — Training data · finalize + nightly compact"]
        direction TB
        GATE -->|"training_data.py<br/>schema v2.0<br/>PII scrub"| SHARDS["~470 rows/day<br/>data/shards/<date>/<hash>.jsonl"]
        SHARDS -->|"upload (53 shards → 59)"| HFD2[("HF dev-autotrain")]
        HFD2 -->|"compact(): collect shards"| COMP["dedupe by content_hash<br/>~418,500 raw → 118,926 gated"]
        COMP -->|"grouped splits<br/>one job can't span train/test"| SPLITS["train 72,800<br/>val 9,099<br/>test 9,228"]
        SPLITS -->|"pairs + card"| HFD2
        HFD2 -->|"data/train|validation|test.parquet"| HFD2
    end

    %% ===================== FLOW 3: CV SEARCH (HOT PATH, USER-FACING) =====================
    subgraph F3["FLOW 3 — CV search · live, SSE"]
        direction TB
        CV["User resume<br/>PDF/txt upload"] -->|"profile extract"| PROF["keywords, skills,<br/>title, location"]
        PROF -->|"keyword scoring"| FTS["index_store FTS5<br/>BM25"]
        PROF -->|"embedding (all-mpnet)"| VEC["semantic_match<br/>cosine"]
        FTS -->|"rank fusion"| RANK["ranked list<br/>match_score + breakdown"]
        VEC -->|"rank fusion"| RANK
        RANK -->|"SSE stream<br/>progress events"| UI["Results view"]
    end

    %% ===================== FLOW 4: TRUST SCORE (RAG) =====================
    subgraph F4["FLOW 4 — Trust score · RAG"]
        direction TB
        JT["Job text"] -->|"embed"| EMB["all-mpnet"]
        JT -->|"title prefix ladder<br/>4→3→2→1 words"| FTS2["FTS5 corpus retrieve<br/>12,780 jobs"]
        FTS2 -->|"top-10 context<br/>+ vector dupes ≥ 0.85"| CTX["RAG context block"]
        CTX -->|"chat_completion<br/>GLM-5.3-flash Tier 2 (flag-gated)<br/>fallback: keyword scorer"| LLM["Teacher LLM<br/>OpenRouter"]
        LLM -->|"strict JSON<br/>5 flags + score 0-100"| OUT["trust-score response<br/>VERIFIED_HIGH_QUALITY …"]
        OUT -->|"append (Step B)"| TL["trust_labels.jsonl<br/>~1,000 rows → student distillation"]
    end

    %% ===================== FLOW 5: CATALOG =====================
    subgraph F5["FLOW 5 — Landing catalog"]
        direction TB
        UK -->|"build_catalog()<br/>12-sector bucketing"| CAT["job_type_catalog.json<br/>8 sectors, 357 today"]
        CAT -->|"exports/ (wiped on rebuild)"| LOCAL["Space disk"]
        CAT -->|"upload_file"| HFD1
        LOCAL -->|"local first"| STRIP["Landing strip"]
        HFD1 -->|"HF fallback via /job-catalog"| STRIP
    end

    GIT -.->|"dataset mirror commit"| GHA["GitHub Actions"]
```

## Key numbers (2026-11-22 refresh)

| Stage | Volume |
|---|---|
| Raw rows written to shards | ~468,900 |
| Pass quality gate | 193,635 (2026-11-19 compact; negative_share 0.238, 0 label conflicts) |
| Published train split | 128,627 rows (`data/train.parquet`) |
| Daily shards on storage | 69 (uploading daily) |
| Live deduped job pool | 12,780 → 10,728 UK |
| Trust labels logged (Step B) | accumulating toward ~1,000 |

*(Numbers from the 2026-11-17 stocktake appear inline in the diagram; this table is the current measurement.)*
