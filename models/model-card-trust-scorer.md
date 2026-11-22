# Model Card — Trust Scorer (RAG + strict-JSON teacher)

## What it does

Scores any UK job posting for **trustworthiness** on two axes:

1. **Five boolean risk flags**
   - `is_ghost_or_stale` — reposted/stale listing patterns
   - `is_resume_harvesting_bot` — "apply via link, no interview" patterns
   - `is_spam` — keyword-driven spam signals
   - `is_fake_or_scam` — fake-employer / external-portal patterns
   - `has_poor_reputation` — layoff/bankruptcy/review signals
2. **A 0–100 trust score** with a four-band classification:
   - ≥80 `VERIFIED_HIGH_QUALITY` · 60–79 `CAUTION_NOISE`
   - 40–59 `LOW_TRUST_HIGH_NOISE` · <40 `BLOCK_SCAM_RISK`

## How it works (retrieval-augmented)

```
job text ──► embed (all-mpnet) ──────────────┐
     │                                        │
     ├─► FTS5/BM25 corpus retrieve            ├──► RAG context block
     │   (title-prefix ladder 4→3→2→1 words,  │
     │    12,780-job corpus)                  │
     ├─► vector duplicate search (cosine) ────┘
     ▼
teacher LLM (strict JSON, scoped system prompt)
     ▼
5 flags + 0–100 score + 1–3 evidence citations
```

Design rules baked into the system prompt:

- Judge **only** the job under evaluation; historical context jobs may be
  cited as duplication evidence, never as character evidence.
- High salary alone is never scam evidence (UK tech legitimately pays 60–120k).
- When in doubt, do not flag — false accusations are worse than a missed flag.

## Teacher cascade (2026-11-22)

- **Tier 2 first:** a frontier-class LLM served through an OpenAI-compatible
  gateway API (vendor deliberately unnamed) when the teacher flag is on
  (one call per scoring request, structured JSON output, quota-guarded at 80%
  gateway-credit use).
- **Fallbacks:** legacy open-source pool → deterministic keyword scorer —
  every failure degrades to a safe default instead of erroring.

## Step B — the labels are the product

Every scored job is appended (schema + job_id + UTC timestamp) to an
append-only label log. At ~1,000 accumulated rows, a **student model
distills the teacher** (Step C) and must beat the teacher's agreement rate
on held-out data before replacing it — the same promotion gate as the tag
classifier.

## Limitations

- The corpus retrieval reflects the platform's own collected jobs — a scam
  pattern never seen before has no history to retrieve.
- Flag thresholds favour precision over recall by design; the score is
  advisory UI signal, not an automated rejection.
- Evidence citations are truncated strings, meant for human review.
