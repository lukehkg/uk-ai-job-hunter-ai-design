# Build it yourself — the 10-step recipe

Everything here was built **solo, part-time, over ~3 months (~1,600 commits),
for ≈ $30 of AI spend + a ~$9/month platform subscription**. The steps below
are the order I'd follow if I started again — including the sequencing
mistakes I'd skip.

Stack used: GitHub Actions (orchestration) · a Python backend (FastAPI) ·
Hugging Face for storage + Spaces (hosting) · SQLite FTS5 + a local
sentence-embedding model for retrieval · small local transformer models for
classification · one frontier-class LLM via an OpenAI-compatible gateway for
verification only.

| # | Step | Time | Cost |
|---|---|---|---|
| 1 | Accounts + storage repos (3 private repos: jobs, training, models) | 1–2 h | $9/mo platform |
| 2 | Daily collection pipeline (2 job-board APIs + scraper + ATS feeds) | 1–2 weeks | API meters |
| 3 | Dedup: content hash + embedding cosine | 3–4 days | $0 |
| 4 | Quality gates + PII scrub | 2 days | $0 |
| 5 | Append-only training shards + nightly compaction | 3–4 days | $0 |
| 6 | Grow the corpus past 10k rows | 2–4 weeks (passive) | $0 |
| 7 | Train the tag classifier locally + grouped-split eval | 1 day | $0 (CPU) |
| 8 | Build the RAG trust scorer | 3–5 days | $0 retrieval |
| 9 | Tier-2 teacher verification + quota guard | 1 day | ~$2 total |
| 10 | Student distillation + automatic promotion gate | ongoing | $0 |

## The steps in detail

**1. Storage layout first.** Three *private* repos on day one: jobs export,
training shards, model artifacts. Separating training data from the jobs
export from the start is what keeps privacy enforceable later.

**2. Collection before intelligence.** Get ~2,000 postings/day flowing with
a scheduled pipeline (cron + a finalize endpoint that merges sources). Don't
build AI until data accumulates — every model below is gated on volume.

**3. Dedup is the highest-leverage component.** Content-hash first, then
embedding cosine ≥ 0.88. It removes ~50% of raw noise, feeds ghost-job
evidence, and guarantees duplicates never consume LLM tokens.

**4. Gates + scrub before storage.** Drop short/empty/spam rows; replace
emails/phones with `[email]`/`[phone]` in every field that will ever be
published. Retrofitting PII scrubbing into an existing corpus is painful —
do it at the door.

**5. Append-only shards, not file rewrites.** One JSONL shard per day
(`shards/<date>/<batch-hash>.jsonl`), idempotent by content hash. A nightly
compaction job collects → dedupes → quality-gates → writes grouped-split
Parquet. Rewriting a growing corpus file is how you lose data.

**6. Let the corpus grow.** 10k quality rows is the minimum for a
respectable classifier. The pipeline accumulates ~470 rows/day — this leg is
calendar time, so start it early and build steps 7–9 while it runs.

**7. Train small, locally.** A 67M-param model on CPU: $0, ~a day. Use
**grouped splits** (group by normalized title+company) so the same job can't
appear in train and test — otherwise your F1 lies to you. Beat a frequency
baseline, not nothing.

**8. RAG trust scorer.** Retrieval (SQLite FTS5 + a local embedding model)
→ context block → one strict-JSON teacher call → 5 flags + score + evidence
citations. The two non-obvious pieces: a **title-prefix ladder** for
retrieval (full text as an FTS query matches nothing) and **scope rules in
the system prompt** so context jobs can't poison the verdict.

**9. Add the Tier-2 teacher only where it pays.** Let the small model label
everything; send *only the low-confidence slice* (~10–20%) to the large
model, with a quota guard that aborts above 80% credit use. Full-corpus
labelling costs ~13× more for ~the same result.

**10. Make promotion automatic.** Log every verdict append-only; nightly,
check whether the student beats the teacher's agreement rate on held-out
data. When it does, swap them. Now the system improves itself.

## 7 lessons learned the hard way

1. **Never paste secrets into docs — assume everything is in history
   forever.** Two credentials ended up in a progress file; both had to be
   rotated. Redaction doesn't rewrite history.
2. **Hosted inference endpoints can break silently** (a handler returned
   400 on every call for weeks). A *local batch* fallback is cheaper and
   immune to that class of failure — it became the primary path.
3. **Build the counter before you need it.** The training set "stopped
   growing" for days because nothing made a missing upload loud. Failures
   must be errors, not warnings.
4. **Grouped splits or your metrics lie.** Near-duplicate listings spanning
   train/test inflated early numbers.
5. **Negatives need mining.** A classifier fed only positives learns
   "everything is a match". Mine negatives from low-score results per
   search batch and hold a target ratio (~0.25).
6. **Tier your model calls.** ~90% of the benefit of a large teacher comes
   from verifying the uncertain 10–20% — the other 80% is waste.
7. **Evaluate against a frequency baseline, not zero.** A multi-label
   model that predicts the top-4 popular tags scores 0.575 F1 for free;
   your model must clearly beat that to be worth serving.
