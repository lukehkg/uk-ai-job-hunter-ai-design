# 3 — Full Solution Architecture (current + planned evolution)

Solid borders = built and live. Dashed borders = designed, not yet built (student model, RAG trust-score UI wiring, per-sector rebalance).

```mermaid
flowchart TB
    %% ================= LAYER 1: SOURCES =================
    subgraph L1["Layer 1 — Ingestion (daily 06:00 UTC)"]
        direction LR
        SRC1["Job-board API A<br/>(commercial feed, primary volume)"]
        SRC2["Job-board API B<br/>(commercial feed)"]
        SRC3["Open web scraper<br/>(major boards, unnamed)"]
        SRC4["Public ATS feeds<br/>(multiple boards)"]
    end

    %% ================= LAYER 2: PROCESSING =================
    subgraph L2["Layer 2 — Processing (FastAPI finalize)"]
        direction LR
        P1["Dedupe<br/>exact keys +<br/>vector ≥ 0.88"]
        P2["UK filter<br/>is_uk_location<br/>16.1% dropped"]
        P3["Risk screening<br/>ghost · spam<br/>harvest flags"]
    end

    %% ================= LAYER 3: DATA PLANE =================
    subgraph L3["Layer 3 — Data plane (HuggingFace, all private)"]
        direction LR
        DATA1[("Jobs repo<br/>pro-data<br/>12,780 → 10,728<br/>canonical feeds")]
        DATA2[("Training repo<br/>dev-autotrain<br/>69 shards · 128,627 train rows<br/>Parquet splits + pairs")]
        DATA3[("Model repo<br/>autotrain-models<br/>C1 distilbert v1<br/>F1 0.888")]
    end

    %% ================= LAYER 4: AI / TRAINING PLANE =================
    subgraph L4["Layer 4 — AI plane"]
        direction LR
        AI1["C1 tag classifier<br/>distilbert · 276 labels<br/>F1 0.888 vs 0.575<br/>LIVE"]
        AI2["E1 embedder<br/>all-mpnet fine-tune<br/>smoke below baseline<br/>scale-up queued"]
        AI3["Trust scorer (RAG)<br/>teacher LLM + FTS5<br/>5 flags + 0-100 score<br/>LIVE"]
        AI4["S1 student distillation<br/>multi-label + regression<br/>needs ~1,000 labels<br/>Step C"]
        AI5["F9 assistant<br/>hosted LLM + RAG<br/>not started"]
    end

    %% ================= LAYER 5: SERVING =================
    subgraph L5["Layer 5 — Serving (HF Space)"]
        direction LR
        SV1["Landing dashboard<br/>sector catalog table<br/>393/day · 12,780 pool"]
        SV2["CV search<br/>semantic + keyword<br/>match breakdown"]
        SV3["Trust badges<br/>risk flags on job cards<br///api/v1/trust-score"]
        SV4["Cover letter / profile<br/>frontier LLM APIs"]
    end

    %% ================= LAYER 6: OPS =================
    subgraph L6["Layer 6 — Ops (GitHub Actions)"]
        direction LR
        OPS1["ci.yml<br/>checks + deploy"]
        OPS2["sync-jobs-oct26<br/>daily 06:00"]
        OPS3["compact-dataset<br/>nightly · green"]
        OPS4["train-student<br/>manual dispatch only"]
    end

    %% ================= FLOWS =================
    L1 --> P1 --> P2 --> P3
    P3 --> DATA1
    P3 --> DATA2
    DATA2 --> AI1
    DATA2 --> AI4
    DATA1 --> AI3
    AI1 --> DATA3
    AI3 --> DATA2

    DATA1 --> SV1
    DATA1 --> SV2
    DATA1 --> SV3
    DATA2 --> SV2

    L6 -.->|"deploy + trigger"| L2
    L6 -.->|"nightly compact"| DATA2

    classDef live fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef planned fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,stroke-dasharray:6 4
    classDef storage fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    class AI1,AI3,AI2 live
    class AI4,AI5 planned
    class DATA1,DATA2,DATA3 storage
```

## Read this diagram as three phases

| Phase | What exists | What is dashed |
|---|---|---|
| **Now** | Full ingestion → dedupe → UK filter → data plane → serving. C1 classifier trained and promoted. Trust scorer live. | — |
| **Next** (Step B/C) | Label accumulation in `trust_labels.jsonl` | S1 student distillation once ~1,000 labels accumulate |
| **Later** | — | F9 assistant (hosted LLM + RAG), per-sector collection rebalance, E1 embedder scale-up |

## The three model tracks (from the MODELS-README decision doc)

1. **C1 tag classifier** (done): distilbert, multi-label over 276 canonical skills, promoted at F1 0.888 vs 0.575 baseline. Serves via in-Space inference or Phase A batch.
2. **E1 embedder** (paused at smoke): fine-tuned all-mpnet for F2 dedup / F3 CV match / F6 semantic search. Smoke recall@5 0.100 vs baseline 0.175 — anchor audit + 20K-pair scale-up queued before retry.
3. **Trust scorer → student** (in progress): RAG teacher running now; labels accumulate; S1 student distills the teacher once the label budget is met, then must beat the teacher's agreement rate to replace it.

## Repo map

```
uklukie/uk-ai-job-hunter-dev          → this repo (code + CI)
uklukie/uk-ai-job-hunter-pro-data     → jobs data (private)
uklukie/uk-ai-job-hunter-dev-autotrain → training shards + splits (private)
uklukie/uk-ai-job-hunter-dev-autotrain-models → model artifacts (private)
uklukie/uk-ai-job-hunter-pro-space    → the live Space (frontend + backend)
```
